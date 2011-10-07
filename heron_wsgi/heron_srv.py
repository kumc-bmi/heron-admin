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
from pyramid.config import Configurator
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound, HTTPSeeOther, HTTPForbidden

# modules in this package
import cas_auth
from cas_auth import route_if_prefix, prefix_router
from usrv import TemplateApp, SessionMiddleware
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

    def configure(self, config, route_name):
        config.add_view(self.get, route_name=route_name, request_method='GET',
                        renderer='index.html')

    def get(self, req):
        from pyramid.response import Response
        parts = self._checklist.parts_for(req.remote_user)
        return dict(parts,
                    # req.route_url('i2b2_login')
                    logout_path=req.route_url('logout'),
                    saa_path=req.route_url('saa'),
                    i2b2_login_path=req.route_url('i2b2_login'),
                    oversight_path=req.route_url('oversight'),
                    #@@ move these to another view
                    done_path=req.route_url('team_done'),
                    team=[],
                    is_data_request='0',
                    uids=' ',
                    candidates=[])


class REDCapLink(object):
    @inject(checklist=Checklist,
            urlopener=URLopener)
    def __init__(self, checklist, urlopener):
        self._m = checklist.medcenter()
        self._hr = checklist.heron_records()
        self._saa_opts = self._hr.saa_opts()
        self._oversight_opts = self._hr.oversight_opts()
        self._urlopener = urlopener

    def configure(self, config, rsaa, rtd):
        config.add_view(self.saa_redir, route_name=rsaa,
                        request_method='GET')
        config.add_view(self.oversight_redir, route_name=rtd,
                        request_method='GET')

    def saa_redir(self, req):
        '''Redirect to a per-user System Access Agreement REDCap survey.

          >>> t, r4 = test_grant_access_with_valid_cas_ticket()
          >>> r5 = t.get('/saa_survey', status=302)
          >>> dict(r5.headers)['Location']
          'http://bmidev1/redcap-host/surveys/?s=8074&full_name=Smith%2C+John&user_id=john.smith'

        Hmm... we're doing a POST to the REDCap API inside a GET.
        Kinda iffy, w.r.t. safety and such.
        '''

        _, uid, full_name = self._request_agent(req)
        return self._survey_redir(self._saa_opts, uid, {
                'user_id': uid, 'full_name': full_name}, req)

    def _request_agent(self, req):
        uid = req.remote_user

        a = self._m.affiliate(uid)
        full_name = "%s, %s" % (a.sn, a.givenname)
        return a, uid, full_name

    def _survey_redir(self, opts, uid, params, req, multi=False):
        rc = redcap_connect.survey_setup(opts, self._urlopener)
        there = self._saa_link = rc(uid, params, multi)
        return HTTPFound(there)

    def oversight_redir(self, req):
        '''Redirect to a per-user sponsorship/data-use REDCap survey.

          >>> t, r4 = test_grant_access_with_valid_cas_ticket()
          >>> r5 = t.get('/team_done', status=302)
          >>> dict(r5.headers)['Location']
          'http://bmidev1/redcap-host/surveys/?s=8074&full_name=Smith%2C+John&is_data_request=0&multi=yes&user_id=john.smith'

        Hmm... we're doing a POST to the REDCap API inside a GET.
        Kinda iffy, w.r.t. safety and such.
        '''

        _, uid, full_name = self._request_agent(req)

        uids = _request_uids(req.GET)

        dr = '1' if req.GET.get('is_data_request', '') == '1' else '0'
        return self._survey_redir(self._oversight_opts, uid,
                                  dict(team_params(self._m, uids),
                                       multi='yes',
                                       user_id=uid, full_name=full_name,
                                       is_data_request=dr),
                                  req, multi=True)


class RepositoryLogin(object):
    @inject(checklist=Checklist,
            pm=i2b2pm.I2B2PM,
            i2b2_tool_addr=KI2B2Address)
    def __init__(self, pm, i2b2_tool_addr, checklist):
        self._hr = checklist.heron_records()
        self._m = checklist.medcenter()
        self._pm = pm
        self._i2b2_tool_addr = i2b2_tool_addr

    def configure(self, config, route):
        config.add_view(self.i2b2_login, route_name=route,
                        request_method='POST')

    def i2b2_login(self, req):
        '''Check credentials, establish account, and loging to i2b2

          >>> t, r1 = test_grant_access_with_valid_cas_ticket()
          >>> r2 = t.post('/i2b2', status=303)
          >>> dict(r2.headers)['Location']
          'http://example/i2b2-webclient'

        '''
        try:
            agt = self._m.affiliate(req.remote_user)
            q = self._hr.q_any(agt)
            a = self._hr.repositoryAccess(q)
            self._pm.ensure_account(a)
            return HTTPSeeOther(self._i2b2_tool_addr)
        except heron_policy.NoPermission, np:
            return HTTPForbidden(detail=np.message)


class HeronAccessPartsApp(object):
    i2b2_login_path='/i2b2'
    oversight_path='/build_team.html'
    oops_path='/oops.html'

    @inject(checklist=Checklist, pm=i2b2pm.I2B2PM,
            urlopener=URLopener,
            i2b2_tool_addr=KI2B2Address)
    def __init__(self, checklist, pm, urlopener, i2b2_tool_addr):
        self._checklist = checklist
        self._pm = pm
        self._m = checklist.medcenter()
        self._i2b2_tool_addr = i2b2_tool_addr

        self._tplapp = TemplateApp(self.parts, self.htdocs)

    def __repr__(self):
        return 'HeronAccessPartsApp(%s, %s, %s)' % (
            self._checklist, self._m, self._i2b2_tool_addr)
    
    def __call__(self, environ, start_response):
        path = environ['PATH_INFO']
        if path.startswith(self.i2b2_login_path):
            return self.i2b2_login(environ, start_response)
        elif path.startswith(self.saa_path):
            return self.saa_redir(environ, start_response)
        elif path.startswith(self.team_done_path):
            return self.oversight_redir(environ, start_response)
        else:
            return self._tplapp(environ, start_response)

    def parts(self, environ, session):
        '''
        .. todo: pass param names such as 'goal' to the template rather than manually maintaining.
        '''
        if 'user' not in session:
            return {}

        path = environ['PATH_INFO']
        if path.startswith(self.oops_path):
            return {}

        params = dict(parse_querystring(environ))
        uids, goal = edit_team(params)

        if goal == 'Search':
            candidates = self._m.affiliateSearch(15,
                                           params.get('cn', ''),
                                           params.get('sn', ''),
                                           params.get('givenname', ''))
            candidates.sort(key = lambda(a): (a.sn, a.givenname))
        else:
            candidates = []

        # Since we're the only supposed to supply these names,
        # it seems OK to throw KeyError if we hit a bad one.
        team = [self._m.affiliate(n) for n in uids]
        team.sort(key = lambda(a): (a.sn, a.givenname))

        base = environ['SCRIPT_NAME']
        parts = dict(self._checklist.parts_for(session['user']),
                     logout_path=base+self.logout_path,
                     saa_path=base+self.saa_path,
                     i2b2_login_path=base+self.i2b2_login_path,
                     oversight_path=base+self.oversight_path,
                     done_path=base+self.team_done_path,
                     team=team,
                     is_data_request=params.get('is_data_request', '0'),
                     uids=' '.join(uids),
                     candidates=candidates)
        return parts


def team_params(mc, uids):
    r'''
    >>> import pprint
    >>> pprint.pprint(list(team_params(medcenter.Mock.make(),
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
              [(i, uids[i], mc.affiliate(uids[i]))
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


ERR_SECTION='errors'
_sample_err_settings = dict(
    debug=False,
    smtp_server='smtp.example.edu',
    error_email='sysadmin@example.edu',
    error_email_from='heron@example.edu',
    error_subject_prefix='HERON crash')


def error_mapper(code, message, environ, global_conf):
    if code in [500]:
        params = {'message':message, 'code':code}
        url = HeronAccessPartsApp.oops_path + '?' + urlencode(params)

        print "@@url:", url
        import pprint
        pprint.pprint(environ)
        return url
    else:
        return None

def err_handler(app, rt, template = 'oops.html'):
    '''
    Error handling needs configuration::

      >>> print TestTimeOptions(_sample_err_settings).inifmt(ERR_SECTION)
      [errors]
      debug=False
      error_email=sysadmin@example.edu
      error_email_from=heron@example.edu
      error_subject_prefix=HERON crash
      smtp_server=smtp.example.edu
    '''

    def handle(environ, start_response):
        try:
            log.debug('path: %s', environ.get('PATH_INFO', ''))
            log.debug('script name: %s', environ['SCRIPT_NAME'])
            return app(environ, start_response)
        except Exception, e:
            exc_info = sys.exc_info()
            try:
                if rt.debug and int(rt.debug):
                    handle_exception(exc_info, environ['wsgi.errors'], debug_mode=True, html=False,
                                     show_exceptions_in_wsgi_errors=True)
                else:
                    handle_exception(exc_info, environ['wsgi.errors'], debug_mode=False, html=False,
                                     show_exceptions_in_wsgi_errors=True,
                                     error_email=rt.error_email,
                                     error_email_from=rt.error_email_from,
                                     smtp_server=rt.smtp_server,
                                     error_subject_prefix=rt.error_subject_prefix)

                # TODO: share loader with the the TemplateApp
                loader = TemplateLoader([HeronAccessPartsApp.htdocs], auto_reload=True)
                tmpl = loader.load(template)
                stream = tmpl.generate(error_info=str(e))
                body = stream.render('xhtml')

                start_response('500 internal server error', [('Content-type', 'text/html;charset=utf-8')])
                return body
            finally:
                exc_info = None
    return handle


class ErrorHandling(injector.Module):
    def configure(self, binder):
        pass

    #@@ @provides(KTopApp)
    #@@ @inject(app=KCASApp, rt=KErrorOptions)
    def err_handler(self, app, rt):
        return err_handler(app, rt)


class HeronAdminConfig(Configurator):
    @inject(guard=cas_auth.Validator,
            settings=KAppSettings,
            cas_rt=(Options, cas_auth.CONFIG_SECTION),
            clv=CheckListView,
            rcv=REDCapLink,
            repo=RepositoryLogin)
    def __init__(self, guard, settings, cas_rt, clv, rcv, repo):
        log.debug('HeronAdminConfig settings: %s', settings)
        Configurator.__init__(self, settings=settings)
        guard.configure(self, cas_rt.app_secret)
        cap_style = cas_auth.CapabilityStyle(guard, cas_auth.PERMISSION)
        self.set_authorization_policy(cap_style)
        self.add_static_view('av', 'heron_wsgi:htdocs-heron/av/',
                             cache_max_age=3600)

        self.add_renderer(name='.html', factory=genshi_render.Factory)

        self.add_route('heron_home', '')
        clv.configure(self, 'heron_home')

        self.add_route('saa', 'saa_survey')
        self.add_route('team_done', 'team_done')
        rcv.configure(self, 'saa', 'team_done')

        self.add_route('i2b2_login', 'i2b2')
        repo.configure(self, 'i2b2_login')

        # todo: views for these routes
        self.add_route('logout', 'logout')
        self.add_route('oversight', 'build_team.html')


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
                                             ['project_id']))

        binder.bind(URLopener,
                    injector.InstanceProvider(urllib2.build_opener()))

        #@@ todo: get this working again. test it?
        binder.bind(KErrorOptions,
                    RuntimeOptions(_sample_err_settings.keys()
                                   ).load(self._webapp_ini, 'errors'))

    @classmethod
    def mods(cls, settings):
        webapp_ini = settings['webapp_ini']
        admin_ini = settings['admin_ini']
        #@@ todo: restore Oops.html error handling and such
        return (cas_auth.RunTime.mods(webapp_ini) +
                [class_(admin_ini)
                 for class_ in i2b2pm.IntegrationTest.deps()]
                + [RunTime(settings)])

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

        binder.bind(KErrorOptions,
                    TestTimeOptions(dict(_sample_err_settings,
                                                debug=True)))


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
