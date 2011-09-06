'''heron_srv.py -- HERON administrative web interface

  >>> print config.TestTimeOptions(_sample_err_settings).inifmt(ERR_SECTION)
  [errors]
  debug=False
  error_email=sysadmin@example.edu
  error_subject_prefix=HERON crash
  from_address=heron@example.edu
  smtp_server=smtp.example.edu


'''
import datetime
from urllib import URLopener
import urllib2

from paste.httpexceptions import HTTPSeeOther, HTTPForbidden
from paste.exceptions.errormiddleware import ErrorMiddleware
from paste.request import parse_querystring
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

KRedcapOptions = injector.Key('RedcapOptions')
KI2B2Address = injector.Key('I2B2Address')
KSearchService = injector.Key('SearchService')
KCASOptions = injector.Key('CASOptions')
KCASApp = injector.Key('CASApp')
KErrorOptions = injector.Key('ErrorOptions')
KTopApp = injector.Key('TopApp')


class HeronAccessPartsApp(object):
    htdocs = 'htdocs-heron/'
    saa_path='/saa_survey'
    i2b2_login_path='/i2b2'
    oversight_path='/build_team.html'

    @inject(checklist=Checklist, medcenter=MedCenter,
            redcap_opts=KRedcapOptions, urlopener=URLopener,
            i2b2_tool_addr=KI2B2Address)
    def __init__(self, checklist, medcenter, redcap_opts, urlopener, i2b2_tool_addr):
        self._checklist = checklist
        self._m = medcenter
        self._redcap_link = redcap_connect.survey_setup(redcap_opts, urlopener)
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

    def saa_redir(self, environ, start_response):
        '''
        Hmm... we're doing a POST to the REDCap API inside a GET.
        Kinda iffy, w.r.t. safety and such.
        '''
        session = environ['beaker.session']
        uid = session['user']

        a = self._m.affiliate(uid)
        full_name = "%s, %s" % (a.sn, a.givenname)
        there = self._redcap_link(uid, {'user_id': uid, 'full_name': full_name})
        return HTTPSeeOther(there).wsgi_application(environ, start_response)

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


class CASWrap(injector.Module):
    def configure(self, binder):
        pass

    @provides(KCASApp)
    @inject(app=HeronAccessPartsApp, cas_settings=KCASOptions)
    def wrap(self, app, cas_settings, session_key='heron',
             auth_area='/', login='/login', logout='/logout'):
        session_opts = cas_auth.make_session(session_key)
        cas_app = cas_auth.cas_required(cas_settings.base, session_opts,
                                        prefix_router, login, logout,
                                        SessionMiddleware(app, session_opts))
        # hmm... not sure app should get requests outside CAS auth_area
        return prefix_router(auth_area, cas_app, app)


ERR_SECTION='errors'
_sample_err_settings = dict(
    debug=False,
    smtp_server='smtp.example.edu',
    error_email='sysadmin@example.edu',
    from_address='heron@example.edu',
    error_subject_prefix='HERON crash')


class ErrorHandling(injector.Module):
    def configure(self, binder):
        pass

    @provides(KTopApp)
    @inject(app=KCASApp, rt=KErrorOptions)
    def err_handler(self, app, rt):
        if rt.debug:
            eh = ErrorMiddleware(app, debug=True,
                                 show_exceptions_in_wsgi_errors=True)
        else:
            eh = ErrorMiddleware(app, debug=False,
                                 error_email=rt.error_email,
                                 from_address=rt.from_address,
                                 smtp_server=rt.smtp_server,
                                 error_subject_prefix=rt.error_subject_prefix,
                                 show_exceptions_in_wsgi_errors=True)
        return eh


class IntegrationTest(injector.Module):
    def configure(self, binder,
                  webapp_ini='integration-test.ini',
                  admin_ini='admin_lib/integration-test.ini',
                  saa_section='saa_survey'):
        searchsvc = ldaplib.LDAPService(admin_ini)
        binder.bind(KSearchService, searchsvc)

        chalkcheck = medcenter.chalkdb_queryfn(admin_ini)
        mc = medcenter.MedCenter(searchsvc, chalkcheck)
        # TODO: use injection for MedCenter
        binder.bind(medcenter.MedCenter, mc)

        i2b2_settings = config.RuntimeOptions('cas_login').load(
            webapp_ini, 'i2b2')
        binder.bind(KI2B2Address, to=i2b2_settings.cas_login)

        binder.bind(KRedcapOptions, redcap_connect.settings(admin_ini, saa_section))
        binder.bind(URLopener, urllib2)

        conn = heron_policy.setup_connection(admin_ini)
        # TODO: use injection for HeronRecords
        hr = heron_policy.HeronRecords(conn, mc, datetime.datetime,
                                       int(survey_settings.survey_id))

        binder.bind(datetime.date, to=datetime.date)
        binder.bind(heron_policy.HeronRecords, to=hr)

        check = Checklist(mc, hr, datetime.date)
        binder.bind(Checklist, check)

        binder.bind(KCASOptions,
                    config.RuntimeOptions('base').load(webapp_ini, 'cas'))
        binder.bind(KErrorOptions,
                    config.RuntimeOptions(_sample_err_settings.keys()
                                          ).load(webapp_ini, 'errors'))


class Mock(injector.Module):
    '''
    >>> depgraph = injector.Injector([Mock(), ErrorHandling(), CASWrap()])
    >>> happ = depgraph.get(HeronAccessPartsApp)
    >>> tapp = depgraph.get(KTopApp)
    '''
    def configure(self, binder):
        binder.bind(KRedcapOptions, redcap_connect._test_settings)
        binder.bind(URLopener,
                    # avoid UnknownProvider: couldn't determine provider ...
                    injector.InstanceProvider(redcap_connect._TestUrlOpener()))
        binder.bind(KI2B2Address, to='http://www.i2b2.org/')

        from admin_lib import hcard_mock
        hd = hcard_mock.MockDirectory()
        binder.bind(KSearchService, to=hd)

        # TODO: use injection for MedCenter
        mc = medcenter.MedCenter(hd, hd.trainedThru)
        binder.bind(medcenter.MedCenter, mc)

        ts = heron_policy._TestTimeSource()
        conn = heron_policy._TestDBConn()
        # TODO: use injection for HeronRecords
        hp = heron_policy.HeronRecords(conn, mc, ts, saa_survey_id=11)

        binder.bind(datetime.date, to=ts)
        binder.bind(heron_policy.HeronRecords, to=hp)

        hp = heron_policy._mock()
        binder.bind(heron_policy.HeronRecords, hp)
        
        cl = Checklist(mc, hp, ts)
        binder.bind(Checklist, cl)

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
    application = injector.Injector([IntegrationTest(),
                                     ErrorHandling(), CASWrap()]).get(KTopApp)
    #application = injector.Injector([Mock(),
    #                                 ErrorHandling(), CASWrap()]).get(KTopApp)


    # In production use, static A/V media files would be
    # served with apache, but for test purposes, we'll use
    # paste DirectoryApp
    app = prefix_router('/av/',
                        fileapp.DirectoryApp(HeronAccessPartsApp.htdocs),
                        application)

    httpserver.serve(app, host=host, port=port)
