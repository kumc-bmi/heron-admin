import datetime

from paste.httpexceptions import HTTPSeeOther

import cas_auth
from usrv import TemplateApp, PathPrefix, SessionMiddleware
from admin_lib import medcenter
from admin_lib import heron_policy
from admin_lib import checklist
from admin_lib.redcap_connect import survey_setup

class HeronAccessPartsApp(TemplateApp):
    def __init__(self, docroot, checklist):
        TemplateApp.__init__(self, docroot)
        self._checklist = checklist

    def parts(self, environ, session):
        if 'user' not in session:
            return {}
        return self._checklist.parts_for(session['user'])


def redcap_redirect(get_addr, medcenter):
    '''Redirect to user-specific REDCap survey.

    Assumes beaker.session with user and full_name.

    Hmm... we're doing a POST to the REDCap API inside a GET.
    Kinda iffy, w.r.t. safety and such.
    '''
    def wsgi(environ, start_response):
        session = environ['beaker.session']
        uid = session['user']

        # perhaps pass full name via session?
        a = medcenter.affiliate(uid)
        full_name = "%s, %s" % (a.sn, a.givenname)
        there = get_addr(uid, full_name)
        return HTTPSeeOther(there).wsgi_application(environ, start_response)

    return wsgi


def _mkapp(cas='https://cas.kumc.edu/cas/', auth_area='/u/',
           login='/u/login', logout='/u/logout',
           saa_survey='/u/saa_survey'):
    
    session_opts = cas_auth.make_session('heron')

    ls = medcenter.ldap_searchfn('admin_lib/kumc-idv.ini', 'idvault')
    cq = medcenter.chalkdb_queryfn('admin_lib/chalk.ini', 'chalk')
    m = medcenter.MedCenter(ls, cq)

    conn = heron_policy.setup_connection(ini='admin_lib/heron_records.ini',
                                         section='heron')
    hr = heron_policy.HeronRecords(conn, m, datetime.date)

    check = checklist.Checklist(m, hr, datetime.date)

    hp = SessionMiddleware(HeronAccessPartsApp('htdocs-heron/', check),
                          session_opts)

    saa_connect = survey_setup('admin_lib/saa_survey.ini', 'redcap')
    srv = PathPrefix(saa_survey, redcap_redirect(saa_connect, m), hp)
    cas = cas_auth.cas_required(cas, session_opts,
                                PathPrefix, login, logout, srv)
    return PathPrefix(auth_area, cas, srv)


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
    app = PathPrefix('/av/', fileapp.DirectoryApp('htdocs-heron/'), application)

    httpserver.serve(app, host=host, port=port)
