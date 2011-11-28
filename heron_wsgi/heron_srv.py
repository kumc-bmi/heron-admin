'''heron_srv.py -- HERON administrative web interface
-----------------------------------------------------

.. todo:: DROC oversight reports

See also: `HERON training materials`__

__ http://informatics.kumc.edu/work/wiki/HERONTrainingMaterials

.. todo:: automated test for LDAP failure

'''

import sys
from urllib import URLopener
import urllib2
import logging
import urlparse

# see setup.py and http://pypi.python.org/pypi
import injector # http://pypi.python.org/pypi/injector/
                # 0.3.1 7deba485e5b966300ef733c3393c98c6
from injector import inject, provides
import sqlalchemy  # leaky; factor out test foo?
import pyramid
from pyramid.config import Configurator
from pyramid.httpexceptions import HTTPFound, HTTPSeeOther, HTTPForbidden

# modules in this package
import cas_auth
import genshi_render
import drocnotice
from admin_lib import medcenter
from admin_lib import heron_policy
from admin_lib.checklist import Checklist
from admin_lib import redcap_connect
from admin_lib import rtconfig
from admin_lib.rtconfig import Options, TestTimeOptions, RuntimeOptions
from admin_lib import disclaimer, redcapdb

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
    t = TestApp(Mock.make()[0].make_wsgi_app())
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
    @inject(checklist=Checklist,
            rt=(Options, heron_policy.SAA_CONFIG_SECTION))
    def __init__(self, checklist, rt):
        self._checklist = checklist
        self._next_route = None
        self._rt = rt

    def issue(self, uidbox, req):
        uid = self._unsealer.unseal(uidbox)
        req.checklist_parts = self._checklist.parts_for(uid)


    def configure(self, config, route_name, next_route):
        config.add_view(self.get, route_name=route_name, request_method='GET',
                        renderer='index.html',
                        permission=heron_policy.PERM_USER)
        self._next_route = next_route

    def get(self, req):
        '''
        >>> from pyramid import testing
        >>> from pyramid.testing import DummyRequest
        >>> config = testing.setUp()
        >>> for route in ('logout', 'saa', 'home', 'oversight', 'i2b2_login'):
        ...     config.add_route(route, route)
        >>> mc, hp, clv = Mock.make((medcenter.MedCenter,
        ...                          heron_policy.HeronRecords,
        ...                          CheckListView))
        >>> clv.configure(config, 'home', 'oversight')
        >>> facreq = DummyRequest()
        >>> facreq.remote_user = 'john.smith'
        >>> mc.issue(facreq) and None
        >>> hp.issue(facreq) and None
        >>> from pprint import pprint
        >>> pprint(clv.get(facreq))
        {'accessDisabled': {'name': 'login'},
         'acknowledgement': None,
         'affiliate': John Smith <john.smith@js.example>,
         'data_use_path': 'http://example.com/oversight',
         'executive': {},
         'faculty': {'checked': 'checked'},
         'i2b2_login_path': 'http://example.com/i2b2_login',
         'logout_path': 'http://example.com/logout',
         'saa_path': 'http://example.com/saa',
         'saa_public': 'http://bmidev1/redcap-host/surveys/?s=43',
         'signatureOnFile': {'checked': 'checked'},
         'sponsored': {'checked': 'checked'},
         'sponsorship_path': 'http://example.com/oversight',
         'trainingCurrent': {'checked': 'checked'},
         'trainingExpiration': '2012-01-01'}

        '''
        value = dict(self._checklist.screen(req.user, req.faculty,
                                            req.executive),
                     # req.route_url('i2b2_login')
                     logout_path=req.route_url('logout'),
                     saa_path=req.route_url('saa'),
                     saa_public=self._rt.survey_url,
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

        there = req.faculty.ensure_oversight_survey(uids, what_for)

        return HTTPFound(there)


class RepositoryLogin(object):
    '''
      # logging.basicConfig(level=logging.DEBUG)
      >>> log.debug ('RepositoryLogin test of disclaimer')

      >>> t, r1 = test_grant_access_with_valid_cas_ticket()
      >>> r2 = t.post('/i2b2', status=303)
      >>> dict(r2.headers)['Location']
      'http://localhost/disclaimer'

      >>> r3 = t.post('/disclaimer', status=303)
      >>> dict(r3.headers)['Location']
      'http://localhost/i2b2'

    .. todo:: fix mock urlopener test interaction so this test works again:
      .>> r3 = t.get('/i2b2', status=303)
      .>> dict(r3.headers)['Location']
      'http://example/i2b2-webclient'
    '''
    @inject(i2b2_tool_addr=KI2B2Address,
            ua=URLopener,
            acks=disclaimer.AcknowledgementsProject)
    def __init__(self, i2b2_tool_addr, ua, acks):
        self._i2b2_tool_addr = i2b2_tool_addr
        self._disclaimer_route = None
        self._ua = ua
        self._acks = acks
        self._login_route = None

    def configure(self, config, route, disclaimer_route):
        config.add_view(self.i2b2_login, route_name=route,
                        permission=heron_policy.PERM_USER)
        config.add_view(self.disclaimer, route_name=disclaimer_route,
                        permission=heron_policy.PERM_USER,
                        renderer='disclaimer.html')
        self._disclaimer_route = disclaimer_route  # mutable state. I'm lazy.
        self._login_route = route

    def i2b2_login(self, req):
        '''Log in to i2b2, provided credentials and current disclaimer.
        '''

        if not req.user.acknowledgement:
            return HTTPSeeOther(req.route_url(self._disclaimer_route))

        try:
            if req.method == 'POST':
                req.user.repository_account().login()
            return HTTPSeeOther(self._i2b2_tool_addr)
        except heron_policy.NoPermission, np:
            return HTTPForbidden(detail=np.message)

    def disclaimer(self, req):
        if req.method == 'GET':
            content, headline = req.disclaimer.content(self._ua)
            return {'url': req.disclaimer.url,
                    'headline': headline,
                    'content': content}
        else:
            self._acks.add_record(req.user.badge.cn, req.disclaimer.url)
            return HTTPSeeOther(req.route_url(self._login_route))


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
    return 1/0


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
    '''
    >>> from paste.fixture import TestApp
    >>> t = TestApp(Mock.make()[0].make_wsgi_app())
    >>> r1 = t.post('/decision_notifier', status=200)
    >>> r1
    <Response 200 OK 'notice sent for reco'>

    '''
    @inject(guard=cas_auth.Validator,
            settings=KAppSettings,
            cas_rt=(Options, cas_auth.CONFIG_SECTION),
            clv=CheckListView,
            rcv=REDCapLink,
            repo=RepositoryLogin,
            tb=TeamBuilder,
            mc=medcenter.MedCenter,
            hr=heron_policy.HeronRecords,
            dn=drocnotice.DROCNotice)
    def __init__(self, guard, settings, cas_rt, clv, rcv, repo, tb, mc, hr, dn):
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
        self.add_route('disclaimer', 'disclaimer')
        repo.configure(self, 'i2b2_login', 'disclaimer')

        self.add_route('logout', 'logout')
        guard.configure(self, 'logout')

        # Decision notifications
        self.add_route('notifier', 'decision_notifier')
        dn.configure(self, 'notifier',
                     permission=pyramid.security.NO_PERMISSION_REQUIRED)

        # for testing
        self.add_route('err', 'err')
        self.add_view(make_internal_error, route_name='err',
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

        binder.bind(URLopener,
                    injector.InstanceProvider(urllib2.build_opener()))

    @provides(medcenter.KAppSecret)
    @inject(rt=(Options, cas_auth.CONFIG_SECTION))
    def cas_app_secret(self, rt):
        return rt.app_secret

    @provides(drocnotice.KMailSettings)
    def settings(self):
        log.debug('mail settings: %s', self._settings)
        return self._settings

    @classmethod
    def mods(cls, settings):
        webapp_ini = settings['webapp_ini']
        admin_ini = settings['admin_ini']
        return (cas_auth.RunTime.mods(webapp_ini) +
                heron_policy.RunTime.mods(admin_ini) +
                [drocnotice.Setup(), RunTime(settings)])

    @classmethod
    def depgraph(cls, settings):
        return injector.Injector(cls.mods(settings))

    @classmethod
    def make(cls, global_config, settings):
        return cls.depgraph(settings).get(HeronAdminConfig)


class Mock(injector.Module, rtconfig.MockMixin):
    '''An injector module to build a mock version of this WSGI application.

    # logging.basicConfig(level=logging.DEBUG)

    Use this module and a couple others to mock up a HeronAdminConfig::
      >>> (c, srt, ort) = Mock.make(
      ...        [HeronAdminConfig,
      ...        (Options, heron_policy.SAA_CONFIG_SECTION),
      ...        (Options, heron_policy.OVERSIGHT_CONFIG_SECTION)])
      >>> type(c)
      <class 'heron_srv.HeronAdminConfig'>

    Then make a WSGI app out of it::
      >>> tapp = c.make_wsgi_app()

    Make sure we override the saa opts so that they have what
    redcap_connect needs, and not just what heron_polic needs::

      >>> srt.domain
      'example.edu'

      >>> ort.project_id
      34

    '''

    stuff = [HeronAdminConfig]

    @classmethod
    def mods(cls):
        return (cas_auth.Mock.mods() + heron_policy.Mock.mods()
                + drocnotice.Mock.mods()
                + [Mock()])

    def configure(self, binder):
        log.debug('configure binder: %s', binder)
        binder.bind(KAppSettings,
                    injector.InstanceProvider({}))

        binder.bind((Options, heron_policy.SAA_CONFIG_SECTION),
                    redcap_connect._test_settings)
        binder.bind((Options, heron_policy.OVERSIGHT_CONFIG_SECTION),
                    redcap_connect._test_settings)

        binder.bind(KI2B2Address, to='http://example/i2b2-webclient')

        binder.bind((Options, cas_auth.CONFIG_SECTION),
                    TestTimeOptions(
                        {'base': 'https://example/cas/',
                         'app_secret': 'sekrit'}))
    @provides(URLopener)
    @inject(smaker=(sqlalchemy.orm.session.Session, redcapdb.CONFIG_SECTION),
            art=(Options, disclaimer.ACKNOWLEGEMENTS_SECTION))
    def web_ua(self, smaker, art):
        return _TestUrlOpener(['yes', 'john.smith'], smaker, art)


class _TestUrlOpener(object):
    '''An URL opener to help with CAS testing
    '''
    def __init__(self, lines, smaker, art):
        self._ua1 = cas_auth.LinesUrlOpener(lines)
        self._ua2 = redcap_connect._TestUrlOpener()
        self._smaker = smaker
        self._art = art

    def open(self, addr, body=None):
        if not body:
            return self._ua1.open(addr)

        params = urlparse.parse_qs(body)
        if 'content' in params:
            if params['content'] == ['survey']:
                return self._ua2.open(addr, body)
            elif params['content'] == ['record']:
                return self.post_record(params)
            else:
                raise IOError, "unknown content param: " + str(params)
        else:
            raise IOError, "no content param: " + str(params)

    def post_record(self, params):
        import json, StringIO

        rows = json.loads(params['data'][0])
        schema = rows[0].keys()
        if sorted(schema) == sorted([u'ack', u'timestamp',
                                     u'disclaimer_address',
                                     u'user_id', u'acknowledgement_complete']):
            values = rows[0]
            record = hash(values['user_id'])
            s = self._smaker()
            heron_policy.add_test_eav(s, self._art.project_id, 1,
                                      record, values.items())
            return StringIO.StringIO('')
        else:
            raise IOError, 'bad request: bad acknowledgement schema: ' + str(schema)


def app_factory(global_config, **settings):
    log.debug('in app_factory')
    config = RunTime.make(global_config, settings)

    # https://pylonsproject.org/projects/pyramid_exclog/dev/
    # self.include('pyramid_exclog')
    config.add_view(server_error_view,
                    renderer='oops.html',
                    context=Exception,
                    permission=pyramid.security.NO_PERMISSION_REQUIRED)

    return config.make_wsgi_app()


if __name__ == '__main__':  # pragma nocover
    # test usage
    from paste import httpserver
    #@@from paste import fileapp
    host, port = sys.argv[1:3]

    logging.basicConfig(level=logging.DEBUG)

    # In production use, static A/V media files would be
    # served with apache, but for test purposes, we'll use
    # paste DirectoryApp
    # TODO: use paster
    #app = prefix_router('/av/',
    #                    fileapp.DirectoryApp(HeronAccessPartsApp.htdocs),
    #                    )

    httpserver.serve(app_factory({},
                                 webapp_ini='integration-test.ini',
                                 admin_ini='admin_lib/integration-test.ini'),
                     host=host, port=port)
