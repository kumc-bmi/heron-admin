'''heron_srv.py -- HERON administrative web interface
'''
import datetime

from paste.httpexceptions import HTTPSeeOther, HTTPForbidden
from paste.exceptions.errormiddleware import ErrorMiddleware
from paste.request import parse_querystring

import cas_auth
from usrv import TemplateApp, SessionMiddleware, route_if_prefix, prefix_router
from admin_lib import medcenter
from admin_lib import ldaplib
from admin_lib import heron_policy
from admin_lib import checklist
from admin_lib import redcap_connect
from admin_lib import config

class HeronAccessPartsApp(object):
    htdocs = 'htdocs-heron/'
    saa_path='/saa_survey'
    i2b2_login_path='/i2b2'
    oversight_path='/build_team.html'

    def __init__(self, checklist, medcenter, saa_redir, i2b2_tool_addr):
        self._checklist = checklist
        self._m = medcenter
        self._saa_redir = saa_redir
        self._i2b2_tool_addr = i2b2_tool_addr

        self._tplapp = TemplateApp(self.parts, self.htdocs)

    def __call__(self, environ, start_response):
        path = environ['PATH_INFO']
        if path.startswith(self.i2b2_login_path):
            return self.i2b2_login(environ, start_response)
        elif path.startswith(self.saa_path):
            return self._saa_redir(environ, start_response)
        else:
            return self._tplapp(environ, start_response)

    def i2b2_login(self, environ, start_response):
        session = environ['beaker.session']
        if environ['REQUEST_METHOD'] == "POST":
            try:
                a = self._checklist.access_for(session['user'])
                ans = HTTPSeeOther(self._i2b2_tool_addr)
            except heron_policy.NoPermission, np:
                ans = HTTPForbidden(detail=np.message).wsgi_application(environ, start_response)
        else:
            ans = HTTPMethodNotAllowed()

        return ans.wsgi_application(environ, start_response)


    def parts(self, environ, session):
        '''
        .. todo: pass param names such as 'goal' to the template rather than manually maintaining.
        '''
        if 'user' not in session:
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
                     saa_path=self.saa_path,
                     i2b2_login_path=self.i2b2_login_path,
                     oversight_path=self.oversight_path,
                     team=team,
                     uids=' '.join(uids),
                     candidates=candidates)
        return parts


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
    v = params.get('uids', None)
    uids = v.split(' ') if v else []

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


def redcap_redirect(get_addr, medcenter):
    '''Redirect to user-specific REDCap survey.

    Assumes beaker.session with user and full_name.

    .. todo: consider caching full_name in session

    Hmm... we're doing a POST to the REDCap API inside a GET.
    Kinda iffy, w.r.t. safety and such.
    '''
    def wsgi(environ, start_response):
        session = environ['beaker.session']
        uid = session['user']

        a = medcenter.affiliate(uid)
        full_name = "%s, %s" % (a.sn, a.givenname)
        there = get_addr(uid, full_name)
        return HTTPSeeOther(there).wsgi_application(environ, start_response)

    return wsgi


def heron_app(searchsvc, chalkcheck, redcapconn, timesrc, survey_settings, i2b2_settings):
    '''
      >>> from admin_lib import hcard_mock
      >>> mockdir = hcard_mock.MockDirectory(hcard_mock.TEST_FILE)
      >>> mockdb = heron_policy._TestDBConn()
      >>> timesrc = heron_policy._TestTimeSource()
      >>> ss = redcap_connect._test_settings
      >>> i2s = config.TestTimeOptions({'cas_login': 'http://...'})
      >>> app = heron_app(mockdir, mockdir.trainedThru, mockdb, timesrc, ss, i2s)
      >>> app == None
      False
    '''
    m = medcenter.MedCenter(searchsvc, chalkcheck)
    hr = heron_policy.HeronRecords(redcapconn, m, timesrc, int(survey_settings.survey_id))
    check = checklist.Checklist(m, hr, datetime.date)
    saa_connect = redcap_connect.survey_setup(survey_settings)
    redir = redcap_redirect(saa_connect, m)
    return HeronAccessPartsApp(check, m, redir, i2b2_settings.cas_login)


def cas_wrap(app, cas_settings,
             auth_area='/', login='/login', logout='/logout'):
    session_opts = cas_auth.make_session('heron')
    cas_app = cas_auth.cas_required(cas_settings.base, session_opts, prefix_router,
                                    login, logout, SessionMiddleware(app, session_opts))
    return prefix_router(auth_area, cas_app, app)


ERR_SECTION='errors'
_sample_err_settings = dict(
    debug=False,
    smtp_server='smtp.example.edu',
    error_email='sysadmin@example.edu',
    from_address='heron@example.edu',
    error_subject_prefix='HERON crash')


def _err_handler(app, rt):
    '''
      >>> print config.TestTimeOptions(_sample_err_settings).inifmt(ERR_SECTION)
      [errors]
      debug=False
      error_email=sysadmin@example.edu
      error_subject_prefix=HERON crash
      from_address=heron@example.edu
      smtp_server=smtp.example.edu
   '''

    if rt.debug:
        eh = ErrorMiddleware(app, debug=True, show_exceptions_in_wsgi_errors=True)
    else:
        eh = ErrorMiddleware(app, debug=False,
                             error_email=rt.error_email,
                             from_address=rt.from_address,
                             smtp_server=rt.smtp_server,
                             error_subject_prefix=rt.error_subject_prefix,
                             show_exceptions_in_wsgi_errors=True)
    return eh


def _mkapp(webapp_ini, admin_ini, saa_section='saa_survey'):
    searchsvc = ldaplib.LDAPService(admin_ini)
    chalkcheck = medcenter.chalkdb_queryfn(admin_ini)
    conn = heron_policy.setup_connection(admin_ini)
    survey_settings = redcap_connect.settings(admin_ini, saa_section)
    i2b2_settings = config.RuntimeOptions('cas_login').load(webapp_ini, 'i2b2')
    happ = heron_app(searchsvc, chalkcheck, conn, datetime.date, survey_settings, i2b2_settings)

    cas_settings = config.RuntimeOptions('base').load(webapp_ini, 'cas')
    # hmm... not sure happ should get requests outside CAS auth_area
    cas_app = cas_wrap(happ, cas_settings)

    err_options = config.RuntimeOptions(_sample_err_settings.keys()).load(webapp_ini, 'errors')
    return _err_handler(cas_app, err_options)


def _integration_test(webapp_ini='integration-test.ini',
                      admin_ini='admin_lib/integration-test.ini'):  # pragma nocover
    return _mkapp(webapp_ini, admin_ini)


# mod_wsgi conventional entry point
#application = _mkapp('heron_pages.ini', 'admin_lib/heron_admin.ini')
application = _integration_test()

if __name__ == '__main__':  # pragma nocover
    # test usage
    from paste import httpserver
    from paste import fileapp
    import sys
    host, port = sys.argv[1:3]

    # In production use, static A/V media files would be
    # served with apache, but for test purposes, we'll use
    # paste DirectoryApp
    app = prefix_router('/av/', fileapp.DirectoryApp(HeronAccessPartsApp.htdocs), application)

    httpserver.serve(app, host=host, port=port)
