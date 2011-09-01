import datetime

from paste.httpexceptions import HTTPSeeOther, HTTPForbidden
from paste.exceptions.errormiddleware import ErrorMiddleware
from paste.request import parse_querystring

import cas_auth
from usrv import TemplateApp, SessionMiddleware, route_if_prefix, prefix_router
from admin_lib import medcenter
from admin_lib import heron_policy
from admin_lib import checklist
from admin_lib.redcap_connect import survey_setup
from admin_lib.config import RuntimeOptions

class HeronAccessPartsApp(object):
    def __init__(self, docroot, checklist, medcenter,
                 saa_redir, saa_path,
                 i2b2_login_path, i2b2_tool_addr,
                 oversight_path):
        self._tplapp = TemplateApp(self.parts, docroot)
        self._checklist = checklist
        self._m = medcenter
        self._saa_redir = saa_redir
        self._saa_path = saa_path
        self._i2b2_login_path = i2b2_login_path
        self._i2b2_tool_addr = i2b2_tool_addr
        self._oversight_path = oversight_path

    def __call__(self, environ, start_response):
        path = environ['PATH_INFO']
        if path.startswith(self._i2b2_login_path):
            return self.i2b2_login(environ, start_response)
        elif path.startswith(self._saa_path):
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
        if 'user' not in session:
            return {}

        team = []
        candidates = []

        params = dict(parse_querystring(environ))
        if params.get('goal', None) == 'Search':
            candidates = self._m.affiliateSearch(15,
                                           params.get('cn', ''),
                                           params.get('sn', ''),
                                           params.get('givenname', ''))

        parts = dict(self._checklist.parts_for(session['user']),
                     saa_path=self._saa_path,
                     i2b2_login_path=self._i2b2_login_path,
                     oversight_path=self._oversight_path,
                     team=team,
                     candidates=candidates)
        return parts


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


def _err_handler(app, ini, section):
    rt = RuntimeOptions("debug smtp_server error_email"
                        " from_address error_subject_prefix".split())
    rt.load(ini, section)
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


def _mkapp(cas='https://cas.kumc.edu/cas/',
           htdocs='htdocs-heron/',
           auth_area='/',
           login='/login', logout='/logout',
           saa_path='/saa_survey',
           i2b2_check='/i2b2', i2b2_tool='https://heron.kumc.edu/i2b2webclient/cas_login.html',
           ini='heron_errors.ini', section='errors'):

    ls = medcenter.LDAPService('admin_lib/kumc-idv.ini', 'idvault')
    cq = medcenter.chalkdb_queryfn('admin_lib/chalk.ini', 'chalk')
    m = medcenter.MedCenter(ls, cq)

    dbini = 'admin_lib/heron_records.ini'
    conn = heron_policy.setup_connection(dbini, section='redcapdb')
    rt = RuntimeOptions(['survey_id'])
    rt.load(dbini, 'saa')
    hr = heron_policy.HeronRecords(conn, m, datetime.date, int(rt.survey_id))

    check = checklist.Checklist(m, hr, datetime.date)
    saa_connect = survey_setup('admin_lib/saa_survey.ini', 'redcap')
    hp = HeronAccessPartsApp(htdocs, check, m,
                             redcap_redirect(saa_connect, m), saa_path,
                             i2b2_check, i2b2_tool, '/build_team.html')

    session_opts = cas_auth.make_session('heron')
    cas = cas_auth.cas_required(cas, session_opts, prefix_router,
                                login, logout, SessionMiddleware(hp, session_opts))

    # hmm... not sure hp should get requests outside auth_area
    return _err_handler(prefix_router(auth_area, cas, hp), ini, section)


# mod_wsgi conventional entry point
application = _mkapp()


if __name__ == '__main__':
    # test usage
    from paste import httpserver
    from paste import fileapp
    import sys
    host, port = sys.argv[1:3]

    # In production use, static A/V media files would be
    # served with apache, but for test purposes, we'll use
    # paste DirectoryApp
    app = prefix_router('/av/', fileapp.DirectoryApp('htdocs-heron/'), application)

    httpserver.serve(app, host=host, port=port)
