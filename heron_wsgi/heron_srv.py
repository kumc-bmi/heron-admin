'''heron_srv.py -- HERON administrative web interface
-----------------------------------------------------

Main features:

@@@@out of date
  * :class:`Validator` restricts access using CAS login
    - see :func:`test_grant_access_with_valid_cas_ticket`

  * :class:`HeronAccessPartsApp` provides:
    - REDCap integration for System Access Agreement
    - I2B2 access to qualified faculty and users they sponsor
    - Investigator requests
      - building a list of people to sponsor
      - REDCap integration

.. todo:: DROC oversight reports

See also: `HERON training materials`__

__ http://informatics.kumc.edu/work/wiki/HERONTrainingMaterials

.. todo:: automated test for LDAP failure
.. todo:: automated test for database failure

'''

import sys
import datetime
from urllib import URLopener, urlencode
import urllib2
import itertools
from os import path
import logging

# see setup.py and http://pypi.python.org/pypi
from paste.exceptions.errormiddleware import handle_exception
from paste.request import parse_querystring
from genshi.template import TemplateLoader
import injector # http://pypi.python.org/pypi/injector/
                # 0.3.1 7deba485e5b966300ef733c3393c98c6
from injector import inject, provides
import pyramid
from pyramid.config import Configurator
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound, HTTPSeeOther, HTTPForbidden

# modules in this package
import cas_auth
from admin_lib import medcenter
from admin_lib.medcenter import MedCenter
from admin_lib import heron_policy
from admin_lib.checklist import Checklist
from admin_lib import redcap_connect
from admin_lib.config import Options, TestTimeOptions, RuntimeOptions
from admin_lib import i2b2pm
import genshi_render

KAppSettings = injector.Key('AppSettings')
KI2B2Address = injector.Key('I2B2Address')
KErrorOptions = injector.Key('ErrorOptions')

log = logging.getLogger(__name__)


def test_home_page_redirects_to_cas():
    '''A plain request for the homepage redirects us to the CAS login page:

      >>> t, r1 = test_home_page_redirects_to_cas()
      >>> dict(r1.headers)['Location']
      'https://example/cas/login?service=http%3A%2F%2Flocalhost%2F'
    '''
    from paste.fixture import TestApp
    heron_policy._test_datasource(reset=True)
    t = TestApp(Mock.make().make_wsgi_app())
    r1 = t.get('/', status=303)
    return t, r1


def test_grant_access_with_valid_cas_ticket(t=None, r2=None):
    '''After CAS login, we validate the ticket and grant access::

      >>> t, r2 = test_home_page_redirects_to_cas()
      >>> t, r4 = test_grant_access_with_valid_cas_ticket(t, r2)
      >>> 'John Smith' in r4
      True
    '''
    if t is None:
        t, r2 = test_home_page_redirects_to_cas()

    r3 = t.get('/?ticket=ST-381409-fsFVbSPrkoD9nANruV4B-example',
               status=302)
    r4 = r3.follow(status=200)
    return t, r4



class CheckListView(object):
    @inject(checklist=Checklist)
    def __init__(self, checklist):
        self._checklist = checklist
        self._next_route = None

    def issue(self, uidbox, req):
        uid = self._unsealer.unseal(uidbox)
        req.checklist_parts = self._checklist.parts_for(uid)


    def configure(self, config, route_name, next_route):
        config.add_view(self.get, route_name=route_name, request_method='GET',
                        renderer='index.html',
                        permission=heron_policy.PERM_USER)
        self._next_route = next_route

    def get(self, req):
        value = dict(self._checklist.screen(req.user, req.faculty,
                                            req.executive),
                     # req.route_url('i2b2_login')
                     logout_path=req.route_url('logout'),
                     saa_path=req.route_url('saa'),
                     i2b2_login_path=req.route_url('i2b2_login'))
        if req.faculty:
            sp = req.route_url(self._next_route,
                               what_for=REDCapLink.for_sponsorship)
            dup = req.route_url(self._next_route,
                                what_for=REDCapLink.for_data_use)
            value = dict(value,
                         sponsorship_path=sp,
                         data_use_path=dup)

        return value


class REDCapLink(object):
    # no longer needs to be a class?

    for_sponsorship = 'sponsorship'
    for_data_use = 'data_use'

    def configure(self, config, rsaa, rtd):
        config.add_view(self.saa_redir, route_name=rsaa,
                        request_method='GET',
                        permission=heron_policy.PERM_USER)
        config.add_view(self.oversight_redir, route_name=rtd,
                        request_method='GET',
                        permission=heron_policy.PERM_FACULTY)

    def saa_redir(self, req):
        '''Redirect to a per-user System Access Agreement REDCap survey.

          >>> t, r4 = test_grant_access_with_valid_cas_ticket()
          >>> r5 = t.get('/saa_survey', status=302)
          >>> dict(r5.headers)['Location']
          'http://bmidev1/redcap-host/surveys/?s=8074&full_name=Smith%2C+John&user_id=john.smith'

        Hmm... we're doing a POST to the REDCap API inside a GET.
        Kinda iffy, w.r.t. safety and such.
        '''

        return HTTPFound(req.user.ensure_saa_survey())

    def oversight_redir(self, req):
        '''Redirect to a per-user sponsorship/data-use REDCap survey.

          >>> t, r4 = test_grant_access_with_valid_cas_ticket()
          >>> r5 = t.get('/team_done/sponsorship', status=302)
          >>> dict(r5.headers)['Location']
          'http://bmidev1/redcap-host/surveys/?s=8074&full_name=Smith%2C+John&multi=yes&user_id=john.smith&what_for=1'

        Hmm... we're doing a POST to the REDCap API inside a GET.
        Kinda iffy, w.r.t. safety and such.
        '''

        uids = _request_uids(req.GET)
        what_for = '2' if req.matchdict['what_for'] == '2' else '1'

        there = req.faculty.ensure_oversight_survey(
            team_params(req.faculty.browser.lookup, uids), what_for)

        return HTTPFound(there)


class RepositoryLogin(object):
    @inject(i2b2_tool_addr=KI2B2Address)
    def __init__(self, i2b2_tool_addr):
        self._i2b2_tool_addr = i2b2_tool_addr

    def configure(self, config, route):
        config.add_view(self.i2b2_login, route_name=route,
                        request_method='POST',
                        permission=heron_policy.PERM_USER)

    def i2b2_login(self, req):
        '''Log in to i2b2, provided credentials.

          >>> t, r1 = test_grant_access_with_valid_cas_ticket()
          >>> r2 = t.post('/i2b2', status=303)
          >>> dict(r2.headers)['Location']
          'http://example/i2b2-webclient'

        '''
        try:
            req.user.repository_account().login()
            return HTTPSeeOther(self._i2b2_tool_addr)
        except heron_policy.NoPermission, np:
            return HTTPForbidden(detail=np.message)


class TeamBuilder(object):
    def configure(self, config, route_name):
        config.add_view(self.get, route_name=route_name,
                        request_method='GET', renderer='build_team.html',
                        permission=heron_policy.PERM_USER)

    def get(self, res, req, max_search_hits=15):
        r'''
          >>> t, r1 = test_grant_access_with_valid_cas_ticket()
          >>> t.get('/build_team/sponsorship', status=200)
          <Response 200 OK '<!DOCTYPE html>\n<htm'>
          >>> c1 = t.get('/build_team/sponsorship?goal=Search&cn=john.smith',
          ...            status=200)
          >>> 'Smith, John' in c1
          True
          >>> done = t.get('/team_done/sponsorship?continue=Done&uids=john.smith',
          ...              status=302)
          >>> dict(done.headers)['Location']
          'http://bmidev1/redcap-host/surveys/?s=8074&full_name=Smith%2C+John&multi=yes&name_etc_1=Smith%2C+John%0AChair+of+Department+of+Neurology%0A&user_id=john.smith&user_id_1=john.smith&what_for=1'
        '''
        params = req.GET
        uids, goal = edit_team(params)

        if goal == 'Search':
            log.debug('cn: %s', params.get('cn', ''))
            candidates = req.user.browser.search(max_search_hits,
                                                 params.get('cn', ''),
                                                 params.get('sn', ''),
                                                 params.get('givenname', ''))
            log.debug('candidates: %s', candidates)
            candidates.sort(key = lambda(a): (a.sn, a.givenname))
        else:
            candidates = []

        # Since we're the only supposed to supply these names,
        # it seems OK to throw KeyError if we hit a bad one.
        team = [req.user.browser.lookup(n) for n in uids]
        team.sort(key = lambda(a): (a.sn, a.givenname))

        what_for = req.matchdict['what_for']
        return dict(done_path=req.route_url('team_done', what_for=what_for),
                    what_for=what_for,
                    team=team,
                    uids=' '.join(uids),
                    candidates=candidates)


def team_params(lookup, uids):
    r'''
    >>> import pprint
    >>> pprint.pprint(list(team_params(medcenter.Mock.make()._lookup,
    ...                                ['john.smith', 'bill.student'])))
    [('user_id_1', 'john.smith'),
     ('name_etc_1', 'Smith, John\nChair of Department of Neurology\n'),
     ('user_id_2', 'bill.student'),
     ('name_etc_2', 'Student, Bill\n\n')]

    '''
    nested = [[('user_id_%d' % (i+1), uid),
               ('name_etc_%d' % (i+1), '%s, %s\n%s\n%s' % (
                    a.sn, a.givenname, a.title, a.ou))]
              for (i, uid, a) in 
              [(i, uids[i], lookup(uids[i]))
               for i in range(0, len(uids))]]
    return itertools.chain.from_iterable(nested)


def edit_team(params):
    r'''
      >>> edit_team({'a_dconnolly': 'on',
      ...            'a_mconnolly': 'on',
      ...            'goal': 'Add',
      ...            'uids': 'rwaitman aallen'})
      (['rwaitman', 'aallen', 'dconnolly', 'mconnolly'], 'Add')

      >>> edit_team({'r_rwaitman': 'on',
      ...            'goal': 'Remove',
      ...            'uids': 'rwaitman aallen'})
      (['aallen'], 'Remove')
    '''
    uids = _request_uids(params)

    goal = params.get('goal', None)
    if goal == 'Add':
        for n in params:
            if params[n] == "on" and n.startswith("a_"):
                uids.append(n[2:])  # hmm... what about dups?
    elif goal == 'Remove':
        for n in params:
            if params[n] == "on" and n.startswith("r_"):
                del uids[uids.index(n[2:])]
    return uids, goal


def _request_uids(params):
    v = params.get('uids', None)
    return v.split(' ') if v else []


def make_internal_error(req):
    x = 1/0


def server_error_view(context, req):
    '''
    @param context: an Exception

    .. todo:: configure pyramid_exclog for sending mail.
    https://pylonsproject.org/projects/pyramid_exclog/dev/
    '''
    log.error('Exception raised: %s', str(context))
    log.debug('Exception trace:', exc_info=context)
    req.response.status = 500
    return dict(error_info=str(context))


class HeronAdminConfig(Configurator):
    @inject(guard=cas_auth.Validator,
            settings=KAppSettings,
            cas_rt=(Options, cas_auth.CONFIG_SECTION),
            clv=CheckListView,
            rcv=REDCapLink,
            repo=RepositoryLogin,
            tb=TeamBuilder,
            mc=medcenter.MedCenter,
            hr=heron_policy.HeronRecords)
    def __init__(self, guard, settings, cas_rt, clv, rcv, repo, tb, mc, hr):
        log.debug('HeronAdminConfig settings: %s', settings)
        Configurator.__init__(self, settings=settings)

        guard.add_issuer(mc)
        guard.add_issuer(hr)

        cap_style = cas_auth.CapabilityStyle([mc, hr])
        self.set_authorization_policy(cap_style)
        self.add_static_view('av', 'heron_wsgi:htdocs-heron/av/',
                             cache_max_age=3600)

        self.add_renderer(name='.html', factory=genshi_render.Factory)

        self.add_route('heron_home', '')
        clv.configure(self, 'heron_home', 'oversight')

        self.add_route('saa', 'saa_survey')
        self.add_route('team_done', 'team_done/{what_for:%s|%s}' % (
                REDCapLink.for_sponsorship,
                REDCapLink.for_data_use))
        rcv.configure(self, 'saa', 'team_done')

        self.add_route('oversight', 'build_team/{what_for:%s|%s}' % (
                REDCapLink.for_sponsorship,
                REDCapLink.for_data_use))
        tb.configure(self, 'oversight')

        self.add_route('i2b2_login', 'i2b2')
        repo.configure(self, 'i2b2_login')

        self.add_route('logout', 'logout')
        guard.configure(self, 'logout')

        # for testing
        self.add_route('err', 'err')
        self.add_view(make_internal_error, route_name='err',
                      permission=pyramid.security.NO_PERMISSION_REQUIRED)

        # https://pylonsproject.org/projects/pyramid_exclog/dev/
        # self.include('pyramid_exclog')
        self.add_view(server_error_view,
                      renderer='oops.html',
                      context=Exception,
                      permission=pyramid.security.NO_PERMISSION_REQUIRED)




class RunTime(injector.Module):
    def __init__(self, settings):
        log.debug('RunTime settings: %s', settings)
        self._settings = settings
        self._webapp_ini = settings['webapp_ini']
        self._admin_ini = settings['admin_ini']

    def configure(self, binder):
        binder.bind(KAppSettings, self._settings)

        i2b2_settings = RuntimeOptions(['cas_login']).load(
            self._webapp_ini, 'i2b2')
        binder.bind(KI2B2Address, to=i2b2_settings.cas_login)

        saa_section = heron_policy.SAA_CONFIG_SECTION
        droc_section = heron_policy.OVERSIGHT_CONFIG_SECTION
        binder.bind((Options, saa_section),
                    redcap_connect.settings(self._admin_ini,
                                            saa_section))
        binder.bind((Options, droc_section),
                     redcap_connect.settings(self._admin_ini,
                                             droc_section,
                                             ['project_id', 'executives']))

        binder.bind(URLopener,
                    injector.InstanceProvider(urllib2.build_opener()))

    @provides(medcenter.KAppSecret)
    @inject(rt=(Options, cas_auth.CONFIG_SECTION))
    def cas_app_secret(self, rt):
        return rt.app_secret

    @classmethod
    def mods(cls, settings):
        webapp_ini = settings['webapp_ini']
        admin_ini = settings['admin_ini']
        return (medcenter.RunTime.mods(admin_ini) +
                cas_auth.RunTime.mods(webapp_ini) +
                heron_policy.RunTime.mods(admin_ini) +
                [RunTime(settings)])

    @classmethod
    def depgraph(cls, settings):
        return injector.Injector(cls.mods(settings))

    @classmethod
    def make(cls, settings):
        return cls.depgraph(settings).get(HeronAdminConfig)


class Mock(injector.Module):
    '''An injector module to build a mock version of this WSGI application.

    # logging.basicConfig(level=logging.DEBUG)

    Use this module and a couple others to mock up a HeronAdminConfig::
      >>> [x.__class__ for x in Mock.mods() if type(x) is type(Mock())]
      [<class 'heron_srv.Mock'>]
      >>> depgraph = Mock.depgraph()
      >>> type(depgraph)
      <class 'injector.Injector'>
      >>> c = Mock.make()
      >>> type(c)
      <class 'heron_srv.HeronAdminConfig'>

    Then make a WSGI app out of it::
      >>> tapp = c.make_wsgi_app()

    Make sure we override the saa opts so that they have what
    redcap_connect needs, and not just what heron_polic needs::

      >>> rt = depgraph.get((Options, heron_policy.SAA_CONFIG_SECTION))
      >>> rt.domain
      'example.edu'

      >>> rt = depgraph.get((Options,
      ...                    heron_policy.OVERSIGHT_CONFIG_SECTION))
      >>> rt.project_id
      34

    '''

    @classmethod
    def make(cls):
        return cls.depgraph().get(HeronAdminConfig)

    @classmethod
    def mods(cls):
        return (cas_auth.Mock.mods() + [
                    i2b2pm.Mock(), heron_policy.Mock(),
                    medcenter.Mock(), Mock()])

    @classmethod
    def depgraph(cls):
        ms = cls.mods()
        log.debug('RunTime mods: %s', ms)
        return injector.Injector(ms)

    def configure(self, binder):
        log.debug('configure binder: %s', binder)
        binder.bind(KAppSettings,
                    injector.InstanceProvider({}))

        binder.bind((Options, heron_policy.SAA_CONFIG_SECTION),
                    redcap_connect._test_settings)
        binder.bind((Options, heron_policy.OVERSIGHT_CONFIG_SECTION),
                    redcap_connect._test_settings)

        binder.bind(URLopener,
                    injector.InstanceProvider(_TestUrlOpener(
                    ['yes', 'john.smith'])))

        binder.bind(KI2B2Address, to='http://example/i2b2-webclient')

        binder.bind((Options, cas_auth.CONFIG_SECTION),
                    TestTimeOptions(
                        {'base': 'https://example/cas/',
                         'app_secret': 'sekrit'}))


class _TestUrlOpener(object):
    '''An URL opener to help with CAS testing
    '''
    def __init__(self, lines):
        from cas_auth import LinesUrlOpener
        self._ua1 = cas_auth.LinesUrlOpener(lines)
        self._ua2 = redcap_connect._TestUrlOpener()

    def open(self, addr, body=None):
        if body:
            return self._ua2.open(addr, body)
        else:
            return self._ua1.open(addr)


#@@ todo: test or delete this
def app_factory(global_config,
                webapp_ini='integration-test.ini',
                admin_ini='admin_lib/integration-test.ini'):
    log.debug('app_factory@@')
    return RunTime.make(dict(webapp_ini=webapp_ini,
                             admin_ini=admin_ini)).make_wsgi_app()


if __name__ == '__main__':  # pragma nocover
    # test usage
    from paste import httpserver
    from paste import fileapp
    import sys
    host, port = sys.argv[1:3]

    logging.basicConfig(level=logging.DEBUG)

    # In production use, static A/V media files would be
    # served with apache, but for test purposes, we'll use
    # paste DirectoryApp
    # TODO: use paster
    app = prefix_router('/av/',
                        fileapp.DirectoryApp(HeronAccessPartsApp.htdocs),
                        app_factory({}))

    httpserver.serve(app, host=host, port=port)
