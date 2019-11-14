'''heron_srv -- HERON administrative web interface
--------------------------------------------------

See also: `HERON training materials`__

__ http://informatics.kumc.edu/work/wiki/HERONTrainingMaterials

.. todo:: automated test for LDAP failure

'''

from urllib import urlencode
import logging

import injector
from injector import inject, provides
import pyramid
from pyramid.config import Configurator
from pyramid.httpexceptions import HTTPFound, HTTPSeeOther, HTTPForbidden
from pyramid_mailer.mailer import Mailer

# modules in this package
import cas_auth
import genshi_render
import drocnotice
import stats
import perf_reports
from admin_lib import medcenter
from admin_lib import heron_policy
from admin_lib import redcap_connect
from admin_lib import rtconfig
from admin_lib.rtconfig import Options, TestTimeOptions
from admin_lib import disclaimer
from admin_lib.ocap_file import WebReadable, Token, Path
import traincheck

KAppSettings = injector.Key('AppSettings')
KI2B2Address = injector.Key('I2B2Address')
KErrorOptions = injector.Key('ErrorOptions')

log = logging.getLogger(__name__)


def test_home_page_redirects_to_cas():
    '''A plain request for the homepage redirects us to the CAS login page:

      >>> t, r1 = test_home_page_redirects_to_cas()
      >>> dict(r1.headers)['Location']
      'https://example/cas/login?service=http%3A%2F%2Fheron-service%2F'

    '''
    from paste.fixture import TestApp
    t = TestApp(Mock.make([HeronAdminConfig])[0].make_wsgi_app())
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


class CheckListView(Token):
    @inject(saa=(redcap_connect.SurveySetup, heron_policy.SAA_CONFIG_SECTION))
    def __init__(self, saa):
        self._next_route = None
        self._saa = saa

    def configure(self, config, route_name, next_route):
        config.add_view(self.get, route_name=route_name, request_method='GET',
                        renderer='index.html',
                        permission=heron_policy.PERM_STATUS)
        self._next_route = next_route

    def get(self, ctx, req):
        '''
        >>> from pyramid import testing
        >>> from pyramid.testing import DummyRequest
        >>> config = testing.setUp()
        >>> for route in ('logout', 'saa', 'dua', 'home', 'oversight',
        ...               'i2b2_login'):
        ...     config.add_route(route, route)
        >>> mc, hp, clv = Mock.make((medcenter.MedCenter,
        ...                          heron_policy.HeronRecords,
        ...                          CheckListView))
        >>> clv.configure(config, 'home', 'oversight')

        >>> stureq = DummyRequest(context=medcenter.AttrDict())
        >>> mc.authenticated('some.one', stureq) and None
        >>> hp.grant(stureq.context, heron_policy.PERM_STATUS)
        >>> stuparts = clv.get(stureq.context, stureq)
        >>> stuparts['affiliate'].is_investigator()
        False

        >>> facreq = DummyRequest(context=medcenter.AttrDict())
        >>> mc.authenticated('john.smith', facreq) and None
        >>> hp.grant(facreq.context, heron_policy.PERM_STATUS)
        >>> from pprint import pprint
        >>> pprint(clv.get(facreq.context, facreq))
        ... # doctest: +NORMALIZE_WHITESPACE
        {'act_sponsorship_path': '/oversight',
         'affiliate': John Smith <john.smith@js.example>,
         'data_use_path': '/oversight',
         'droc': {},
         'dua_path': '/dua',
         'executive': {},
         'faculty': {'checked': 'checked'},
         'greenheron_use_path': '/oversight',
         'i2b2_login_path': '/i2b2_login',
         'logout_path': '/logout',
         'repositoryAccess': {'checked': 'checked'},
         'saa_path': '/saa',
         'saa_public': 'http://testhost/redcap-host/surveys/?s=43',
         'signatureOnFile': {'checked': 'checked'},
         'sponsored': {},
         'sponsorship_path': '/oversight',
         'trainingCurrent': {'checked': 'checked'},
         'trainingLast': Training(username='john.smith',
                                  expired='2012-01-01', completed='2012-01-01',
                                  course='Human Subjects 101')}

        >>> execreq = DummyRequest(context=medcenter.AttrDict())
        >>> mc.authenticated('big.wig', execreq) and None
        >>> hp.grant(execreq.context, heron_policy.PERM_STATUS)
        >>> execparts = clv.get(execreq.context, execreq)
        >>> execparts['sponsorship_path']
        '/oversight'
        >>> execparts['data_use_path']
        '/oversight'
        '''
        status = ctx.status

        def yn(x):  # genshi attrs
            return {'checked': 'checked'} if x else {}

        sp = req.route_path(self._next_route,
                           what_for=REDCapLink.for_sponsorship)
        asp = req.route_path(self._next_route,
                             what_for=REDCapLink.for_act_sponsorship)
        ghp = req.route_path(self._next_route,
                             what_for=REDCapLink.for_greenheron_use)
        dup = req.route_path(self._next_route,
                            what_for=REDCapLink.for_data_use)

        parts = dict(affiliate=ctx.badge,
                     trainingCurrent=yn(status.current_training),
                     trainingLast=(status.current_training
                                   or status.expired_training),
                     signatureOnFile=yn(status.system_access_signed),
                     repositoryAccess=yn(status.complete),
                     faculty=yn(status.faculty),
                     executive=yn(status.executive),
                     droc=yn(status.droc),
                     sponsored=yn(status.sponsored),
                     sponsorship_path=sp,
                     act_sponsorship_path=asp,
                     greenheron_use_path=ghp,
                     data_use_path=dup,
                     i2b2_login_path=req.route_path('i2b2_login'),
                     logout_path=req.route_path('logout'),
                     saa_path=req.route_path('saa'),
                     saa_public=self._saa.base,
                     dua_path=req.route_path('dua'))

        log.info('GET %s: %s', req.url,
                 [(k, parts.get(k, None)) for k in ('affiliate',
                                                    'trainingExpiration',
                                                    'sponsorship_path',
                                                    'executive')])
        return parts


class REDCapLink(Token):
    for_sponsorship = 'sponsorship'
    for_data_use = 'data_use'
    for_act_sponsorship = 'act_sponsorship'
    for_greenheron_use = 'greenheron_use'

    def configure(self, config, rsaa, rtd, dua):
        config.add_view(self.saa_redir, route_name=rsaa,
                        request_method='GET',
                        permission=heron_policy.PERM_SIGN_SAA)
        config.add_view(self.dua_redir, route_name=dua,
                        request_method='GET',
                        permission=heron_policy.PERM_SIGN_DUA)
        config.add_view(self.oversight_redir, route_name=rtd,
                        request_method='GET',
                        permission=heron_policy.PERM_OVERSIGHT_REQUEST)

    def saa_redir(self, context, req):
        '''Redirect to a per-user System Access Agreement REDCap survey.

          >>> t, r4 = test_grant_access_with_valid_cas_ticket()
          >>> r5 = t.get('/saa_survey', status=302)
          >>> dict(r5.headers)['Location'].split('&')
          ... # doctest: +NORMALIZE_WHITESPACE
          ['http://testhost/redcap-host/surveys/?s=aqFVbr',
           'full_name=Smith%2C+John', 'user_id=john.smith']

        Hmm... we're doing a POST to the REDCap API inside a GET.
        Kinda iffy, w.r.t. safety and such.
        '''
        sign_saa = context.sign_saa
        there = sign_saa.ensure_saa_survey()
        log.info('GET SAA at %s: -> %s', req.url, there)
        return HTTPFound(there)

    def dua_redir(self, context, req):
        '''Redirect to a per-user Data Use Agreement REDCap survey.

          >>> t, r4 = test_grant_access_with_valid_cas_ticket()
          >>> r5 = t.get('/dua_survey', status=302)
          >>> dict(r5.headers)['Location'].split('&')
          ... # doctest: +NORMALIZE_WHITESPACE
          ['http://testhost/redcap-host/surveys/?s=aqFVbr',
           'full_name=Smith%2C+John', 'user_id=john.smith']

        Hmm... we're doing a POST to the REDCap API inside a GET.
        Kinda iffy, w.r.t. safety and such.
        '''

        sign_dua = context.sign_dua
        there = sign_dua.ensure_dua_survey()
        log.info('GET DUA at %s: -> %s', req.url, there)
        return HTTPFound(there)

    def oversight_redir(self, context, req):
        '''Redirect to a per-user sponsorship/data-use REDCap survey.

          >>> t, r4 = test_grant_access_with_valid_cas_ticket()
          >>> r5 = t.get('/team_done/sponsorship?investigator=john.smith',
          ...  status=302)
          >>> dict(r5.headers)['Location'].split('&')
          ... # doctest: +NORMALIZE_WHITESPACE
          ['http://testhost/redcap-host/surveys/?s=aqFVbr',
           'faculty_email=john.smith%40js.example',
           'faculty_name=Smith%2C+John',
           'full_name=Smith%2C+John',
           'multi=yes', 'request_from_faculty=1', 'user_id=john.smith',
           'what_for=1']

          >>> r6 = t.get('/team_done/data_use?investigator=john.smith',
          ...     status=302)
          >>> dict(r6.headers)['Location'].split('&')
          ... # doctest: +NORMALIZE_WHITESPACE
          ['http://testhost/redcap-host/surveys/?s=aqFVbr',
           'faculty_email=john.smith%40js.example',
           'faculty_name=Smith%2C+John',
           'full_name=Smith%2C+John',
           'multi=yes', 'request_from_faculty=1', 'user_id=john.smith',
           'what_for=2']

        Hmm... we're doing a POST to the REDCap API inside a GET.
        Kinda iffy, w.r.t. safety and such.
        '''

        oversight_request = context.oversight_request
        uids = _request_uids(req.GET)

        fac_id = req.GET.get('investigator')
        if not fac_id:
            raise IOError('bad request')

        label = req.matchdict['what_for']
        what_for = (heron_policy.HeronRecords.DATA_USE
                    if (label == REDCapLink.for_data_use)
                    else heron_policy.HeronRecords.GREENHERON_USE
                    if (label == REDCapLink.for_greenheron_use)
                    else heron_policy.HeronRecords.ACT_SPONSORSHIP
                    if (label == REDCapLink.for_act_sponsorship)
                    else heron_policy.HeronRecords.SPONSORSHIP)

        there = oversight_request.ensure_oversight_survey(
            uids, fac_id, what_for)
        log.info('GET oversight at %s: -> %s', req.url, there)

        return HTTPFound(there)


class RepositoryLogin(Token):
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

    TODO: CSRF tokens

    '''
    @inject(i2b2_tool_addr=KI2B2Address,
            rdblog=(WebReadable, disclaimer.DISCLAIMERS_SECTION),
            acks=disclaimer.AcknowledgementsProject)
    def __init__(self, i2b2_tool_addr, rdblog, acks):
        self._i2b2_tool_addr = i2b2_tool_addr
        self._disclaimer_route = None
        self._rdblog = rdblog
        self._acks = acks
        self._login_route = None

    def configure(self, config, route, disclaimer_route):
        config.add_view(self.i2b2_login, route_name=route,
                        permission=heron_policy.PERM_START_I2B2)
        config.add_view(self.disclaimer, route_name=disclaimer_route,
                        permission=heron_policy.PERM_START_I2B2,
                        renderer='disclaimer.html')
        self._disclaimer_route = disclaimer_route  # mutable state. I'm lazy.
        self._login_route = route

    def i2b2_login(self, ctx, req):
        '''Log in to i2b2, provided credentials and current disclaimer.
        '''
        start_i2b2 = ctx.start_i2b2

        try:
            authz = start_i2b2()
        except KeyError:
            log.info('i2b2_login: redirect to disclaimer')
            return HTTPSeeOther(req.route_path(self._disclaimer_route))
        except heron_policy.NoPermission as np:
            log.error('i2b2_login: NoPermission')
            return HTTPForbidden(detail=np.message)

        log.info('i2b2_login: redirect to i2b2')
        user_id, password = authz.creds()
        there = '%s?%s' % (self._i2b2_tool_addr,
                           urlencode(dict(user_id=user_id,
                                          password=password)))
        return HTTPSeeOther(there)

    def disclaimer(self, context, req):
        '''
        TODO: check CSRF token
        '''
        disclaimers = context.disclaimers

        disclaimer = disclaimers.current_disclaimer()
        if req.method == 'GET':
            log.info('GET disclaimer: %s', disclaimer.url)
            content, headline = disclaimer.content(self._rdblog)
            return {'url': disclaimer.url,
                    'headline': headline,
                    'content': content}
        else:
            badge = context.badge
            self._acks.add_record(badge.cn, disclaimer.url)
            log.info('POST disclaimer: added %s %s; redirecting to login',
                     badge.cn, disclaimer.url)
            return HTTPSeeOther(req.route_path(self._login_route))


class TeamBuilder(Token):
    def configure(self, config, route_name):
        config.add_view(self.get, route_name=route_name,
                        request_method='GET', renderer='build_team.html',
                        permission=medcenter.PERM_BADGE)

    def get(self, context, req, max_search_hits=15):
        r'''Get team builder page template data.

        If a user follows the sponsorship link, they should get a
        document::

          >>> t, r1 = test_grant_access_with_valid_cas_ticket()
          >>> t.get('/build_team/sponsorship', status=200)
          <Response 200 OK '<!DOCTYPE html>\n<htm'>

        A search for user id `john.smith` includes his name in the
        response::

          >>> c1 = t.get('/build_team/sponsorship?goal=Search&cn=john.smith',
          ...            status=200)
          >>> 'Smith, John' in c1
          True

        Submitting with the Done button takes us to a REDCap form with
        bits filled in::

          >>> done = t.get('/team_done/sponsorship?continue=Done'
          ...              '&uids=john.smith&investigator=john.smith',
          ...              status=302)
          >>> dict(done.headers)['Location'].split('&')
          ... # doctest: +NORMALIZE_WHITESPACE +ELLIPSIS
          ['http://testhost/redcap-host/surveys/?s=aqFVbr',
           'faculty_email=john.smith%40js.example',
           'faculty_name=Smith%2C+John',
           'full_name=Smith%2C+John',
           'multi=yes',
           'name_etc_1=Smith%2C+John%0AChair+...+Neurology%0ANeurology',
           'request_from_faculty=1',
           'team_email_1=john.smith%40js.example',
           'user_id=john.smith', 'user_id_1=john.smith', 'what_for=1']

        '''
        badge = context.badge
        browser = context.browser
        executives = context.executives

        params = req.GET
        uids, goal, investigator_id = edit_team(params, badge, executives)

        candidates, studyTeam = [], []

        if goal == 'Search':
            log.debug('cn: %s', params.get('cn', ''))
            candidates = browser.search(max_search_hits,
                                        params.get('cn', ''),
                                        params.get('sn', ''),
                                        params.get('givenname', ''))
            log.debug('candidates: %s', candidates)
            candidates.sort(key=lambda(a): (a.sn, a.givenname))
        else:
            if goal == 'Lookup':
                log.debug('study id: %s', params.get('studyId', ''))
                studyTeam = browser.studyTeam(params.get('studyId', ''))
                log.debug('study team members: %s', studyTeam)
                studyTeam.sort(key=lambda who: (who["lastName"],
                                                who["firstName"]))

        # Since we're the only supposed to supply these names,
        # it seems OK to throw KeyError if we hit a bad one.
        team = [browser.lookup(n) for n in uids]
        team.sort(key=lambda(a): (a.sn, a.givenname))

        investigator = None
        if investigator_id:
            inv_info = browser.lookup(investigator_id)
            if inv_info.faculty_role() or investigator_id in executives:
                investigator = inv_info

        what_for = req.matchdict['what_for']
        log.info('TeamBuilder.get: %d candidates, %d in team',
                 len(candidates), len(team))
        return dict(done_path=req.route_path('team_done', what_for=what_for),
                    what_for=what_for,
                    investigator=investigator,
                    team=team,
                    uids=' '.join(uids),
                    studyTeam=studyTeam,
                    faculty_check=medcenter.MedCenter.faculty_check,
                    executives=executives,
                    candidates=candidates)


def edit_team(params, requestor,
              executives=[]):
    r'''Compute team resulting from edits

    The team starts with the user who is building the request::

      >>> from admin_lib.notary import makeNotary
      >>> notary = makeNotary()
      >>> stu = medcenter.IDBadge(notary,
      ...    kumcPersonJobcode='Undergrad', kumcPersonFaculty='N',
      ...    cn='bill.student')
      >>> edit_team({}, stu)
      (['bill.student'], '', None)

    If the requestor is faculty, we infer it's the sponsor::
      >>> fac = medcenter.IDBadge(notary,
      ...    kumcPersonJobcode='1234', kumcPersonFaculty='Y',
      ...    cn='john.smith')
      >>> edit_team({}, fac)
      (['john.smith'], '', 'john.smith')

    We can add team members::
      >>> edit_team({'a_dconnolly': 'on',
      ...            'a_mconnolly': 'on',
      ...            'goal': 'Add',
      ...            'uids': 'rwaitman aallen'}, stu)
      (['aallen', 'dconnolly', 'mconnolly', 'rwaitman'], 'Add', None)

    And add a sponsor::
      >>> edit_team({'a_rwaitman': 'on',
      ...            'goal': 'Add Faculty',
      ...            'uids': 'rwaitman aallen'}, stu)
      (['aallen', 'rwaitman'], 'Add Faculty', 'rwaitman')

    And add an executive sponsor::
      >>> edit_team({'a_bill.student': 'on',
      ...            'goal': 'Add Faculty',
      ...            'uids': 'u1'}, stu, ['bill.student'])
      (['bill.student', 'u1'], 'Add Faculty', 'bill.student')

    Or remove team members::
      >>> edit_team({'r_rwaitman': 'on',
      ...            'goal': 'Remove',
      ...            'uids': 'rwaitman aallen'}, 'u1')
      (['aallen'], 'Remove', None)

    Or remove the sponsor::
      >>> edit_team({'goal': 'Remove', 'r_fac1': 'on',
      ...            'investigator': 'fac1',
      ...            'uids': 'fac1 stu1'}, stu)
      (['stu1'], 'Remove', None)
    '''
    uids = _request_uids(params) if params else [requestor.cn]

    fac_choice = (params.get('investigator') if params
                  else requestor.cn if (
                          requestor.is_faculty() or
                          requestor.cn in executives)
                  else None)

    goal = params.get('goal', '')
    if 'Add' in goal:
        for n in sorted(params):
            if params[n] == "on" and n.startswith("a_"):
                uids.append(n[2:])

                if 'Faculty' in goal:
                    fac_choice = n[2:]

    elif goal == 'Remove':
        for n in params:
            if params[n] == "on" and n.startswith("r_"):
                uid = n[len("r_"):]
                del uids[uids.index(uid)]
                if fac_choice == uid:
                    fac_choice = None
    return sorted(set(uids)), goal, fac_choice


def _request_uids(params):
    v = params.get('uids', None)
    return v.split(' ') if v else []


def _make_internal_error(req):
    return 1 / 0


def server_error_view(context, req):
    '''
    @param context: an Exception

    .. todo:: configure pyramid_exclog for sending mail.
    https://pylonsproject.org/projects/pyramid_exclog/dev/
    '''
    log.error('Exception raised: %s', str(context))
    log.warn('Exception trace:', exc_info=context)
    req.response.status = 500
    return dict(error_info=str(context))


class HeronAdminConfig(Configurator):
    '''
    >>> from paste.fixture import TestApp
    >>> t = TestApp(Mock.make([HeronAdminConfig])[0].make_wsgi_app())
    >>> r1 = t.post('/decision_notifier', status=200)
    >>> r1
    <Response 200 OK 'notice sent for reco'>

    '''
    @inject(guard=cas_auth.Validator,
            casopts=(Options, cas_auth.CONFIG_SECTION),
            conf=KAppSettings,
            clv=CheckListView,
            rcv=REDCapLink,
            repo=RepositoryLogin,
            tb=TeamBuilder,
            mc=medcenter.MedCenter,
            hr=heron_policy.HeronRecords,
            dn=drocnotice.DROCNotice,
            report=stats.Reports,
            perf=perf_reports.PerformanceReports)
    def __init__(self, guard, casopts, conf, clv, rcv,
                 repo, tb, mc, hr, dn, report, perf):
        log.debug('HeronAdminConfig settings: %s', conf)

        Configurator.__init__(self, settings=conf)

        cas_auth.CapabilityStyle.setup(self, casopts.app_secret,
                                       'logout', 'logout',
                                       mc.authenticated,
                                       [mc, hr], guard)

        self.add_static_view('av', 'heron_wsgi:templates/av/',
                             cache_max_age=3600)

        self.add_renderer(name='.html', factory=genshi_render.Factory)

        self.add_route('heron_home', '')
        clv.configure(self, 'heron_home', 'oversight')

        self.add_route('saa', 'saa_survey')
        self.add_route('dua', 'dua_survey')
        self.add_route('team_done', 'team_done/{what_for:%s|%s|%s|%s}' % (
                REDCapLink.for_sponsorship,
                REDCapLink.for_act_sponsorship,
                REDCapLink.for_greenheron_use,
                REDCapLink.for_data_use))
        rcv.configure(self, 'saa', 'team_done', 'dua')

        self.add_route('oversight', 'build_team/{what_for:%s|%s|%s|%s}' % (
                REDCapLink.for_sponsorship,
                REDCapLink.for_act_sponsorship,
                REDCapLink.for_greenheron_use,
                REDCapLink.for_data_use))
        tb.configure(self, 'oversight')

        self.add_route('i2b2_login', 'i2b2')
        self.add_route('disclaimer', 'disclaimer')
        repo.configure(self, 'i2b2_login', 'disclaimer')

        # Decision notifications
        self.add_route('notifier', 'decision_notifier')
        dn.configure(self, 'notifier',
                     permission=pyramid.security.NO_PERMISSION_REQUIRED)

        # Usage reports
        report.configure(self, 'reports/')

        # Performance reports
        perf.configure(self, 'reports/')

        # for testing
        self.add_route('err', 'err')
        self.add_view(_make_internal_error, route_name='err',
                      permission=pyramid.security.NO_PERMISSION_REQUIRED)


class RunTime(rtconfig.IniModule):  # pragma: nocover
    def __init__(self, ini, settings, mailer):
        log.debug('RunTime settings: %s', settings)
        rtconfig.IniModule.__init__(self, ini)
        self._settings = settings
        self.__mailer = mailer

    @provides(KAppSettings)
    def settings(self):
        return self._settings

    @provides(KI2B2Address)
    def addr(self):
        return self.get_options(['cas_login'], section='i2b2').cas_login

    @provides(Mailer)
    def mailer(self):
        return self.__mailer

    @classmethod
    def mods(cls, cwd, settings, mailer, create_engine, **kwargs):
        ini = cwd / settings['webapp_ini']
        admin_ini = cwd / settings['admin_ini']
        trainingfn = traincheck.from_config(admin_ini, create_engine)
        return (cas_auth.RunTime.mods(ini=ini, **kwargs) +
                heron_policy.RunTime.mods(ini=admin_ini,
                                          create_engine=create_engine,
                                          trainingfn=trainingfn,
                                          **kwargs) +
                [cls(ini, settings, mailer)])


class Mock(injector.Module, rtconfig.MockMixin):
    '''An injector module to build a mock version of this WSGI application.

    # logging.basicConfig(level=logging.DEBUG)

    Test precursors to HeronAdminConfig

    >>> Mock.make([cas_auth.Validator, KAppSettings, CheckListView])
    [Validator(cas_addr=https://example/cas/), {}, CheckListView()]

    >>> Mock.make([REDCapLink, RepositoryLogin, TeamBuilder])
    [REDCapLink(), RepositoryLogin(), TeamBuilder()]

    >>> Mock.make([medcenter.MedCenter, heron_policy.HeronRecords])
    [MedCenter(directory_service, training), HeronRecords()]

    >>> Mock.make([drocnotice.DROCNotice, stats.Reports])
    [DROCNotice(), Reports()]

    Use this module and a couple others to mock up a HeronAdminConfig::
      >>> (c, src, orc) = Mock.make(
      ...        [HeronAdminConfig,
      ...        (redcap_connect.SurveySetup,
      ...         heron_policy.SAA_CONFIG_SECTION),
      ...        (redcap_connect.SurveySetup,
      ...         heron_policy.OVERSIGHT_CONFIG_SECTION)])
      >>> c.__class__.__name__
      'HeronAdminConfig'

    Then make a WSGI app out of it::
      >>> tapp = c.make_wsgi_app()

    Make sure we override the saa opts so that they have what
    redcap_connect needs, and not just what heron_policy needs::

      >>> src.domain
      'js.example'

      >>> orc.project_id
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

        binder.bind(KI2B2Address, to='http://example/i2b2-webclient')

        binder.bind((Options, cas_auth.CONFIG_SECTION),
                    TestTimeOptions(
                        {'base': 'https://example/cas/',
                         'app_secret': 'sekrit'}))


def app_factory(global_config, **settings):
    from datetime import datetime
    from io import open as io_open
    from os import listdir
    from os.path import join as joinpath
    from random import Random
    from urllib2 import build_opener
    import uuid

    from sqlalchemy import create_engine
    import ldap

    cwd = Path('.', open=io_open, joinpath=joinpath, listdir=listdir)

    log.debug('in app_factory')
    [config] = RunTime.make(
        [HeronAdminConfig],
        cwd=cwd,
        settings=settings,
        create_engine=create_engine,
        ldap=ldap,
        uuid=uuid,
        urlopener=build_opener(),
        timesrc=datetime,
        rng=Random(),
        mailer=Mailer.from_settings(settings))

    # https://pylonsproject.org/projects/pyramid_exclog/dev/
    # self.include('pyramid_exclog')
    config.add_view(server_error_view,
                    renderer='oops.html',
                    context=Exception,
                    permission=pyramid.security.NO_PERMISSION_REQUIRED)

    return config.make_wsgi_app()


if __name__ == '__main__':  # pragma nocover
    def _script():
        from sys import argv

        from paste import httpserver
        # using paste to serve /templates/av/ past the proxy
        host, port = argv[1:3]

        logging.basicConfig(level=logging.DEBUG)

        httpserver.serve(
            app_factory({},
                        webapp_ini='integration-test.ini',
                        admin_ini='admin_lib/integration-test.ini'),
            host=host, port=port)

    _script()
