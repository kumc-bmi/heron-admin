'''heron_srv.py -- HERON administrative web interface

  >>> print config.TestTimeOptions(_sample_err_settings).inifmt(ERR_SECTION)
  [errors]
  debug=False
  error_email=sysadmin@example.edu
  error_email_from=heron@example.edu
  error_subject_prefix=HERON crash
  smtp_server=smtp.example.edu


'''
import datetime
from urllib import URLopener, urlencode
import urllib2
import itertools

from paste.httpexceptions import HTTPSeeOther, HTTPForbidden
from paste.exceptions.errormiddleware import handle_exception
from paste.request import parse_querystring
from genshi.template import TemplateLoader
import injector # http://pypi.python.org/pypi/injector/
                # 0.3.1 7deba485e5b966300ef733c3393c98c6
from injector import inject, provides

import cas_auth
from usrv import TemplateApp, SessionMiddleware, route_if_prefix, prefix_router
from admin_lib import medcenter
from admin_lib.medcenter import MedCenter
from admin_lib import ldaplib
from admin_lib import heron_policy
from admin_lib.checklist import Checklist
from admin_lib import redcap_connect
from admin_lib import config
from admin_lib import i2b2pm

KI2B2Address = injector.Key('I2B2Address')
KCASOptions = injector.Key('CASOptions')
KCASApp = injector.Key('CASApp')
KErrorOptions = injector.Key('ErrorOptions')
KTopApp = injector.Key('TopApp')


class HeronAccessPartsApp(object):
    htdocs = 'htdocs-heron/'
    base_path='/'
    login_path='/login'
    logout_path='/logout'
    saa_path='/saa_survey'
    team_done_path='/team_done'
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
        self._hr = checklist.heron_records()
        self._saa_opts = self._hr.saa_opts()
        self._oversight_opts = self._hr.oversight_opts()
        self._urlopener = urlopener
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

    def i2b2_login(self, environ, start_response):
        session = environ['beaker.session']
        if environ['REQUEST_METHOD'] == "POST":
            try:
                agt = self._m.affiliate(session['user'])
                q = self._hr.q_any(agt)
                a = self._hr.repositoryAccess(q)
                self._pm.ensure_account(a)
                ans = HTTPSeeOther(self._i2b2_tool_addr)
            except heron_policy.NoPermission, np:
                ans = HTTPForbidden(detail=np.message).wsgi_application(environ, start_response)
        else:
            ans = HTTPMethodNotAllowed()

        return ans.wsgi_application(environ, start_response)

    def saa_redir(self, environ, start_response):
        '''
        Hmm... we're doing a POST to the REDCap API inside a GET.
        Kinda iffy, w.r.t. safety and such.
        '''
        _, uid, full_name = self._request_agent(environ)
        return self._survey_redir(self._saa_opts, uid, {'user_id': uid, 'full_name': full_name},
                                  environ, start_response)

    def _request_agent(self, environ):
        session = environ['beaker.session']
        uid = session['user']

        a = self._m.affiliate(uid)
        full_name = "%s, %s" % (a.sn, a.givenname)
        return a, uid, full_name

    def _survey_redir(self, opts, uid, params, environ, start_response, multi=False):
        there = self._saa_link = redcap_connect.survey_setup(opts, self._urlopener)(uid, params, multi)
        return HTTPSeeOther(there).wsgi_application(environ, start_response)

    def oversight_redir(self, environ, start_response):
        _, uid, full_name = self._request_agent(environ)

        params = dict(parse_querystring(environ))
        uids = _request_uids(params)

        return self._survey_redir(self._oversight_opts, uid,
                                  dict(team_params(self._m, uids),
                                       multi='yes',
                                       user_id=uid, full_name=full_name,
                                       is_data_request='0'),
                                  environ, start_response, multi=True)

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

        parts = dict(self._checklist.parts_for(session['user']),
                     logout_path=self.logout_path,
                     saa_path=self.saa_path,
                     i2b2_login_path=self.i2b2_login_path,
                     oversight_path=self.oversight_path,
                     done_path=self.team_done_path,
                     team=team,
                     uids=' '.join(uids),
                     candidates=candidates)
        return parts


def team_params(mc, uids):
    r'''
    >>> import pprint
    >>> pprint.pprint(list(team_params(medcenter.Mock.make(), ['john.smith', 'bill.student'])))
    [('user_id_1', 'john.smith'),
     ('name_etc_1', 'Smith, John\nChair of Department of Neurology\n'),
     ('user_id_2', 'bill.student'),
     ('name_etc_2', 'Student, Bill\n\n')]

    '''
    nested = [[('user_id_%d' % (i+1), uid),
               ('name_etc_%d' % (i+1), '%s, %s\n%s\n%s' % (a.sn, a.givenname, a.title, a.ou))]
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


class CASWrap(injector.Module):
    def configure(self, binder):
        pass

    @provides(KCASApp)
    @inject(app=HeronAccessPartsApp, cas_settings=KCASOptions)
    def wrap(self, app, cas_settings, session_key='heron'):
        session_opts = cas_auth.make_session(session_key)
        cas_app = cas_auth.cas_required(cas_settings.base, session_opts,
                                        prefix_router, app.login_path, app.logout_path,
                                        SessionMiddleware(app, session_opts))
        return prefix_router(app.base_path, cas_app, app)


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
    def handle(environ, start_response):
        try:
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

    @provides(KTopApp)
    @inject(app=KCASApp, rt=KErrorOptions)
    def err_handler(self, app, rt):
        return err_handler(app, rt)


class IntegrationTest(injector.Module):
    @classmethod
    def depgraph(cls,
                 admin_ini='admin_lib/integration-test.ini'):
        return injector.Injector([IntegrationTest(),
                                  ErrorHandling(), CASWrap()] +
                                 [class_(admin_ini)
                                  for class_ in i2b2pm.IntegrationTest.deps()])

    def configure(self, binder,
                  webapp_ini='integration-test.ini'):
        i2b2_settings = config.RuntimeOptions('cas_login').load(
            webapp_ini, 'i2b2')
        binder.bind(KI2B2Address, to=i2b2_settings.cas_login)

        binder.bind(URLopener,
                    injector.InstanceProvider(urllib2.build_opener()))

        binder.bind(KCASOptions,
                    config.RuntimeOptions('base').load(webapp_ini, 'cas'))
        binder.bind(KErrorOptions,
                    config.RuntimeOptions(_sample_err_settings.keys()
                                          ).load(webapp_ini, 'errors'))


class Mock(injector.Module):
    '''An injector module to build a mock version of this WSGI application.

    Use this module and a couple others to mock up to HeronAccessPartsApp::
      >>> depgraph = Mock.depgraph()
      >>> happ = depgraph.get(HeronAccessPartsApp)

    Then automatically inject it into a CAS and Error handling wrappers::
      >>> tapp = depgraph.get(KTopApp)

    An initial visit to the root page redirects to the login path and sets a cookie::
      >>> from paste.fixture import TestApp
      >>> t = TestApp(tapp)
      >>> r1 = t.get('/', status=303)
      >>> ('location', happ.login_path) in r1.headers
      True
      >>> ['Found cookie' for (n, v) in r1.headers if n.lower() == 'set-cookie']
      ['Found cookie']

    what happens when we follow?
      >>> r2 = r1.follow()


    .. todo:: automated test for LDAP failure
    '''

    @classmethod
    def depgraph(cls):
        return injector.Injector([Mock(), ErrorHandling(), CASWrap(),
                                  i2b2pm.Mock(), heron_policy.Mock(),
                                  medcenter.Mock()])

    def configure(self, binder):
        binder.bind(URLopener,
                    # avoid UnknownProvider: couldn't determine provider ...
                    injector.InstanceProvider(redcap_connect._TestUrlOpener()))

        binder.bind(KI2B2Address, to='http://www.i2b2.org/')

        binder.bind(KCASOptions,
                    config.TestTimeOptions(
                        {'base': 'https://cas.kumc.edu/cas/'}))

        binder.bind(KErrorOptions,
                    config.TestTimeOptions(dict(_sample_err_settings,
                                                debug=True)))

                    
if __name__ == '__main__':  # pragma nocover
    # test usage
    from paste import httpserver
    from paste import fileapp
    import sys
    host, port = sys.argv[1:3]

    # mod_wsgi conventional entry point @@needs to be global
    application = IntegrationTest().depgraph().get(KTopApp)

    # In production use, static A/V media files would be
    # served with apache, but for test purposes, we'll use
    # paste DirectoryApp
    # TODO: use paster
    app = prefix_router('/av/',
                        fileapp.DirectoryApp(HeronAccessPartsApp.htdocs),
                        application)

    httpserver.serve(app, host=host, port=port)
