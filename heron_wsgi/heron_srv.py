import datetime

from paste.httpexceptions import HTTPSeeOther
from paste.exceptions.errormiddleware import ErrorMiddleware

import cas_auth
from usrv import TemplateApp, SessionMiddleware, route_if_prefix, prefix_router
from admin_lib import medcenter
from admin_lib import heron_policy
from admin_lib import checklist
from admin_lib.redcap_connect import survey_setup
from admin_lib.config import RuntimeOptions

class HeronAccessPartsApp(object):
    def __init__(self, docroot, checklist, saa_redir, saa_path):
        self._tplapp = TemplateApp(self.parts, docroot)
        self._checklist = checklist
        self._saa_redir = saa_redir
        self._saa_path = saa_path

    def __call__(self, environ, start_response):
        return route_if_prefix(self._saa_path, self._saa_redir, self._tplapp,
                               environ, start_response)
        
    def parts(self, environ, session):
        if 'user' not in session:
            return {}
        parts = dict(self._checklist.parts_for(session['user']),
                     saa_path=self._saa_path)
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
           ini='heron_errors.ini', section='errors'):
    

    ls = medcenter.LDAPService('admin_lib/kumc-idv.ini', 'idvault')
    cq = medcenter.chalkdb_queryfn('admin_lib/chalk.ini', 'chalk')
    m = medcenter.MedCenter(ls, cq)

    conn = heron_policy.setup_connection(ini='admin_lib/heron_records.ini',
                                         section='heron')
    hr = heron_policy.HeronRecords(conn, m, datetime.date)
    check = checklist.Checklist(m, hr, datetime.date)
    saa_connect = survey_setup('admin_lib/saa_survey.ini', 'redcap')
    hp = HeronAccessPartsApp(htdocs, check,
                             redcap_redirect(saa_connect, m), saa_path)
                          
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
