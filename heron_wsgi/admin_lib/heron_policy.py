'''heron_policy.py -- HERON policy decisions, records
-----------------------------------------------------

:class:`HeronRecords` implements the `HERON governance`__ policies.

__ http://informatics.kumc.edu/work/wiki/HERON#governance

.. For debugging, change .. to >>>.
.. logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
  >>> import sys; logging.basicConfig(level=logging.INFO, stream=sys.stdout)

View-only access for Qualified Faculty
======================================

Excerpting from `HERON training materials`__:

  For qualified faculty who want view-only access to do patient count
  queries, executing a system access agreement is the only
  requirement.

__ http://informatics.kumc.edu/work/wiki/HERONTrainingMaterials

  >>> hp, mc, oc = Mock.make((HeronRecords, medcenter.MedCenter,
  ...                         OversightCommittee))
  INFO:cache_remote:OversightCommittee@1 cache initialized
  INFO:cache_remote:HeronRecords@1 cache initialized

Recalling the login protocol from :mod:`heron_wsgi.cas_auth`::

  >>> def _login(uid, mc, hp, perm):
  ...     req = medcenter.MockRequest()
  ...     mc.authenticated(uid, req)
  ...     hp.grant(req.context, perm)
  ...     return req

Dr. Smith has signed the system access agreement and is current on his
human subjects training, so he can access the repository and make
investigator requests::

  >>> facreq = _login('john.smith', mc, hp, PERM_STATUS)
  INFO:cache_remote:system access query for ('SAA', 'john.smith@js.example')
  INFO:cache_remote:... cached until 2011-09-02 00:00:15.500000
  INFO:cache_remote:in DROC? query for john.smith
  INFO:cache_remote:... cached until 2011-09-02 00:01:00.500000
  >>> facreq.context.status  # doctest: +NORMALIZE_WHITESPACE
  Status(current_training='2012-01-01', droc=None, executive=False,
         expired_training=None, faculty=True, sponsored=None,
         system_access_signed=[datetime.datetime(2011, 8, 26, 0, 0)])

He can follow the "start i2b2" link:
  >>> facreq = _login('john.smith', mc, hp, PERM_START_I2B2)

But he has yet to acknowledge the disclaimer:

  >>> authz = facreq.context.start_i2b2()
  Traceback (most recent call last):
    ...
  KeyError: 'john.smith'

Once he acknowledges it, he can access the repository:

  >>> facreq.context.disclaimers.current_disclaimer()
  ... # doctest: +NORMALIZE_WHITESPACE
  Disclaimer(disclaimer_id=1, url=http://example/blog/item/heron-release-xyz,
             current=1)
  >>> facreq.context.disclaimers.ack_disclaimer(facreq.context.badge)
  >>> facreq.context.start_i2b2()
  INFO:i2b2pm:Finding I2B2 project for REDCap pids: []
  INFO:i2b2pm:User REDCap projects are not in HERON
  Access(John Smith <john.smith@js.example>)

Unforgeable System Access Agreement
***********************************

:meth:`HeronRecords.grant` also issues an :class:`Affiliate` user
capability, which provides a link to an authenticated system access
survey, using :mod:`heron_wsgi.admin_lib.redcap_connect`::

  >>> facreq = _login('john.smith', mc, hp, PERM_SIGN_SAA)
  >>> facreq.context.sign_saa.ensure_saa_survey().split('?')
  ... # doctest: +NORMALIZE_WHITESPACE
  INFO:cache_remote:SAA link query for ('SAA', 'john.smith')
  INFO:cache_remote:... cached until 2011-09-02 00:00:16.500000
  ['http://testhost/redcap-host/surveys/',
   's=f1f9&full_name=Smith%2C+John&user_id=john.smith']

Sponsored Users
===============

Bill cannot access the HERON repository because he is neither
faculty not sponsored, nor has he completed human subjects training::

  >>> stureq = _login('bill.student', mc, hp, PERM_STATUS)
  INFO:cache_remote:Sponsorship query for ('sponsorship', 'bill.student')
  INFO:heron_policy:not sponsored: bill.student
  INFO:cache_remote:... cached until 2011-09-03 00:00:02
  INFO:heron_policy:no training on file for: bill.student (Bill Student)
  INFO:cache_remote:system access query for ('SAA', 'bill.student@js.example')
  INFO:cache_remote:... cached until 2011-09-02 00:00:17.500000
  INFO:cache_remote:in DROC? query for bill.student
  INFO:cache_remote:... cached until 2011-09-02 00:01:01.500000
  >>> stureq.context.status  #doctest: +NORMALIZE_WHITESPACE
  Status(current_training=None, droc=None, executive=False,
         expired_training=None, faculty=False,
         sponsored=False, system_access_signed=[])

  >>> stureq = _login('bill.student', mc, hp, PERM_START_I2B2)
  ... # doctest: +NORMALIZE_WHITESPACE
  Traceback (most recent call last):
    ...
  NoPermission: NoPermission(Status(current_training=None, droc=None,
                                    executive=False, expired_training=None,
                                    faculty=False, sponsored=False,
                                    system_access_signed=[]))

Verify that remote accesses are cached:

  >>> stureq = _login('bill.student', mc, hp, PERM_START_I2B2)
  ... # doctest: +ELLIPSIS
  Traceback (most recent call last):
    ...
  NoPermission: ...

.. note:: We count on sqlalchemy to recover from errors in the connection
   to the database of sponsorship records.

Another student has been sponsored and is current on training, but has
not yet executed the system access agreement::

  >>> stu2req = _login('some.one', mc, hp, PERM_START_I2B2)
  ... #doctest: +NORMALIZE_WHITESPACE
  Traceback (most recent call last):
    ...
  NoPermission: NoPermission(Status(current_training='2012-01-01',
            droc=None, executive=False,
            expired_training=None, faculty=False, sponsored=True,
            system_access_signed=[]))

This student does have authorization to sign the SAA:

  >>> stu2req = _login('some.one', mc, hp, PERM_SIGN_SAA)
  WARNING:medcenter:missing LDAP attribute ou for some.one
  WARNING:medcenter:missing LDAP attribute title for some.one
  >>> stu2req.context.sign_saa
  Affiliate(some.one)

This student's sponsor is not with KUMC anymore

  >>> stureq = _login('jill.student', mc, hp, PERM_STATUS)
  ... #doctest: +NORMALIZE_WHITESPACE
  INFO:cache_remote:Sponsorship query for ('sponsorship', 'jill.student')
  WARNING:heron_policy:Sponsor prof.fickle not at med center anymore.
  INFO:heron_policy:not sponsored: jill.student
  INFO:cache_remote:... cached until 2011-09-03 00:00:06
  INFO:cache_remote:system access query for ('SAA', 'jill.student@js.example')
  INFO:cache_remote:... cached until 2011-09-02 00:00:21.500000
  INFO:cache_remote:in DROC? query for jill.student
  INFO:cache_remote:... cached until 2011-09-02 00:01:03.500000

Exception for executives from participating institutions
=======================================================

Executives don't need sponsorship::

  >>> exreq = _login('big.wig', mc, hp, PERM_START_I2B2)
  INFO:cache_remote:system access query for ('SAA', 'big.wig@js.example')
  INFO:cache_remote:... cached until 2011-09-02 00:00:22
  INFO:cache_remote:in DROC? query for big.wig
  INFO:cache_remote:... cached until 2011-09-02 00:01:04


Investigator Requests
=====================

Faculty and executives can make sponsorship and data usage requests to
the oversight committee::

  >>> facreq = _login('john.smith', mc, hp, PERM_INVESTIGATOR_REQUEST)
  >>> facreq.context.investigator_request
  InvestigatorRequest(from=john.smith)

  >>> facreq.context.investigator_request.ensure_oversight_survey(
  ...        ['some.one'], what_for=HeronRecords.DATA_USE).split('&')
  ... # doctest: +NORMALIZE_WHITESPACE
  WARNING:medcenter:missing LDAP attribute ou for some.one
  WARNING:medcenter:missing LDAP attribute title for some.one
  ['http://testhost/redcap-host/surveys/?s=f1f9',
   'full_name=Smith%2C+John',
   'multi=yes',
   'name_etc_1=One%2C+Some%0A%0A',
   'user_id=john.smith',
   'user_id_1=some.one',
   'what_for=2']


  >>> exreq = _login('big.wig', mc, hp, PERM_INVESTIGATOR_REQUEST)
  >>> ok = exreq.context.investigator_request.ensure_oversight_survey(
  ...        ['some.one'], what_for=HeronRecords.DATA_USE).split('&')
  WARNING:medcenter:missing LDAP attribute ou for some.one
  WARNING:medcenter:missing LDAP attribute title for some.one


Overight Auditing
=================

Oversight committee members can get sensitive audit info::

  >>> exreq = _login('big.wig', mc, hp, PERM_DROC_AUDIT)

Ordinary users cannot, though they can get aggregate usage info::

  >>> stureq = _login('bill.student', mc, hp, PERM_STATS_REPORTER)
  >>> stureq.context.stats_reporter
  I2B2AggregateUsage()

  >>> stureq = _login('bill.student', mc, hp, PERM_DROC_AUDIT)
  Traceback (most recent call last):
    ...
  NotDROC


'''

from datetime import timedelta
import itertools
import logging
from collections import namedtuple

import injector
from injector import inject, provides, singleton
from sqlalchemy import orm
from sqlalchemy.sql import and_

from ocap_file import Token
import rtconfig
import i2b2pm
import medcenter
import redcap_connect
import redcapdb
import noticelog
from noticelog import OVERSIGHT_CONFIG_SECTION
import disclaimer
from audit_usage import I2B2AggregateUsage, I2B2SensitiveUsage
from cache_remote import Cache

SAA_CONFIG_SECTION = 'saa_survey'

PERM_STATUS = __name__ + '.status'
PERM_SIGN_SAA = __name__ + '.sign_saa'
PERM_INVESTIGATOR_REQUEST = __name__ + 'investigator_request'
PERM_START_I2B2 = __name__ + '.start_i2b2'
PERM_DROC_AUDIT = __name__ + '.droc_audit'
PERM_STATS_REPORTER = __name__ + '.stats_reporter'
PERM_START_I2B2 = 'start_i2b2'

log = logging.getLogger(__name__)


@singleton
class OversightCommittee(Token, Cache):
    @inject(redcap_sessionmaker=(orm.session.Session,
                                 redcapdb.CONFIG_SECTION),
            oversight_rc=(redcap_connect.SurveySetup,
                          OVERSIGHT_CONFIG_SECTION),
            mc=medcenter.MedCenter,
            timesrc=rtconfig.Clock,
            auditor=I2B2SensitiveUsage,
            dr=noticelog.DecisionRecords)
    def __init__(self, redcap_sessionmaker, oversight_rc, mc,
                 timesrc, auditor, dr):
        Cache.__init__(self, timesrc.now)
        self.__rcsm = redcap_sessionmaker
        self.project_id = oversight_rc.project_id
        self.__mc = mc
        self.inspector = mc.getInspector()
        self.__auditor = auditor
        self.__dr = dr

    @classmethod
    def _memberq(cls, pid, who):
        '''
        >>> print OversightCommittee._memberq(238, 'big.wig')
        ... #doctest: +NORMALIZE_WHITESPACE
        SELECT redcap_user_rights.project_id, redcap_user_rights.username
        FROM redcap_user_rights
        WHERE redcap_user_rights.project_id = :project_id_1
        AND redcap_user_rights.username = :username_1
        '''
        t = redcapdb.redcap_user_rights
        return t.select().\
            where(t.c.project_id == pid).\
            where(t.c.username == who)

    def _droc_auditor(self, alleged_badge,
                     ttl=timedelta(seconds=60)):
        badge = self.inspector.vouch(alleged_badge)

        def db_q():
            s = self.__rcsm()
            ans = s.execute(self._memberq(self.project_id, badge.cn))

            in_droc = len(ans.fetchall()) == 1
            return ttl, in_droc

        in_droc = self._query(badge.cn, db_q, 'in DROC?')
        if not in_droc:
            raise NotDROC

        return (self.__auditor, self.__dr)


Status = namedtuple('Status',
                    sorted(dict(faculty=0, executive=0, sponsored=0,
                                droc=0,
                                current_training=0, expired_training=0,
                                system_access_signed=0).keys()))


def sufficient(s):
    return ((s.faculty or s.executive or s.sponsored) and s.current_training
            and s.system_access_signed)


class HeronRecords(Token, Cache):
    '''

    In the oversight_project, userid of sponsored users are stored in
    REDCap fields with names like user_id_% and approval decisions are
    stored in fields with names like approve_%, with a distinct
    approve_% field for each participating institution.

    >>> from ddict import DataDict
    >>> ddict = DataDict('oversight')
    >>> dd_orgs = [n[len('approve_'):] for (n, etc) in ddict.fields()
    ...            if n.startswith('approve_')]
    >>> set(dd_orgs) == set(noticelog.DecisionRecords.institutions)
    True

    >>> len([n for (n, etc) in ddict.fields() if n.startswith('user_id_')]) > 3
    True


    >>> uses = ddict.radio('what_for')
    >>> HeronRecords.oversight_request_purposes == tuple(
    ...     [ix for (ix, label) in uses])
    True

    .. todo:: check expiration date
    '''

    SPONSORSHIP = '1'
    DATA_USE = '2'
    oversight_request_purposes = (SPONSORSHIP, DATA_USE)

    @inject(mc=medcenter.MedCenter,
            pm=i2b2pm.I2B2PM,
            dr=noticelog.DecisionRecords,
            stats=I2B2AggregateUsage,
            saa_rc=(redcap_connect.SurveySetup,
                    SAA_CONFIG_SECTION),
            oversight_rc=(redcap_connect.SurveySetup,
                          OVERSIGHT_CONFIG_SECTION),
            oc=OversightCommittee,
            dg=disclaimer.DisclaimerGuard,
            smaker=(orm.session.Session,
                    redcapdb.CONFIG_SECTION),
            timesrc=rtconfig.Clock)
    def __init__(self, mc, pm, dr, stats, saa_rc, oversight_rc, oc,
                 dg, smaker, timesrc):
        Cache.__init__(self, timesrc.now)
        log.debug('HeronRecords.__init__ again?')
        self._smaker = smaker
        self._mc = mc
        self._pm = pm
        self.__dr = dr
        self.__stats = stats
        self._t = timesrc
        self._saa_survey_id = saa_rc.survey_id
        self._saa_rc = saa_rc
        self._oversight_rc = oversight_rc
        self.__oc = oc
        self._oversight_project_id = oversight_rc.project_id
        self.__dg = dg

        def repository_authz(badge):
            rc_pids = self._redcap_rights(badge.cn)
            project_id, _ = pm.i2b2_project(rc_pids)
            return pm.account_for(badge, project_id)
        self.__redeem = dg.make_redeem(repository_authz)

    def authenticated(self, uid, req):
        return []

    def grant(self, context, p):
        log.debug('HeronRecords.grant(%s, %s)' % (context, p))

        badge = self._mc.idbadge(context)
        context.badge = badge

        if p is PERM_STATUS:
            context.status = self._status(badge)
        elif p is PERM_SIGN_SAA:
            context.sign_saa = Affiliate(badge, self._query, self._saa_rc)
        elif p is PERM_INVESTIGATOR_REQUEST:
            context.investigator_request = self._investigator_request(badge)
        elif p is PERM_DROC_AUDIT:
            audit, dr = self.__oc._droc_auditor(badge)
            context.droc_audit = audit
            context.decision_records = dr
        elif p is PERM_STATS_REPORTER:
            context.stats_reporter = self.__stats
            context.browser = self._mc._browser
        elif p is PERM_START_I2B2:
            st = self._status(badge)
            if not sufficient(st):
                raise NoPermission(st)
            context.start_i2b2 = lambda: self.__redeem(badge)
            context.disclaimers = self.__dg
        else:
            raise TypeError

    def _status(self, badge):
        sponsored = (None if badge.is_investigator()
                     else
                     (self._sponsorship(badge.cn) is not None))

        current_training, expired_training = self._training_current(badge)
        system_access_sigs = [sig.completion_time
                              for sig in self._signatures(badge.mail)]

        try:
            droc_audit = self.__oc._droc_auditor(badge)
        except NotDROC:
            droc_audit = None

        return Status(faculty=badge.is_faculty(),
                      executive=badge.is_executive(),
                      sponsored=sponsored,
                      droc=droc_audit,
                      current_training=current_training,
                      expired_training=expired_training,
                      system_access_signed=system_access_sigs)

    def _sponsorship(self, uid,
                     ttl=timedelta(seconds=600)):
        def do_q():
            for ans in self.__dr.sponsorships(uid):
                try:
                    self._mc._browser.lookup(ans.sponsor)
                except KeyError:
                    log.warn('Sponsor %s not at med center anymore.',
                             ans.sponsor)
                else:
                    log.info('sponsorship OK: %s', ans)
                    return ttl, ans

            log.info('not sponsored: %s', uid)
            return timedelta(1), None

        return self._query(('sponsorship', uid), do_q, 'Sponsorship')

    def _training_current(self, badge):
        try:
            when = self._mc.trained_thru(badge)
        except (IOError):
            log.warn('failed to look up training due to IOError')
            log.debug('training error detail', exc_info=True)
            return None, None
        except LookupError:
            log.info('no training on file for: %s (%s)',
                     badge.cn, badge.full_name())
            return None, None

        current = when >= self._t.today().isoformat()
        if not current:
            log.info('training expired %s for: %s (%s)',
                     when, badge.cn, badge.full_name())

        return (when, None) if current else (None, when)

    def _signatures(self, mail,
                   ttl=timedelta(seconds=15)):
        '''Look up SAA survey response by email address.
        '''

        def q():
            return ttl, self._smaker().execute(
                _saa_query(mail, self._saa_survey_id)).fetchall()

        return self._query(('SAA', mail), q, 'system access')

    def _investigator_request(self, badge):
        log.debug('investigator_request: %s faculty? %s executive? %s',
                  badge, badge.is_faculty(), badge.is_executive())

        if not (badge.is_investigator()):
            raise medcenter.NotFaculty

        return InvestigatorRequest(badge, self._mc._browser,
                                   self._oversight_rc)

    def _redcap_rights(self, uid):
        r = redcapdb.redcap_user_rights
        return [row.project_id for row in self._smaker().\
                execute(r.select(r.c.project_id).\
                where(r.c.username == uid))]


def _saa_query(mail, survey_id):
    '''
      >>> q = _saa_query('john.smith@js.example', 11)
      >>> print str(q)
      ... # doctest: +NORMALIZE_WHITESPACE
      SELECT r.response_id, r.participant_id, r.record,
      r.first_submit_time, r.completion_time, r.return_code,
      p.participant_id, p.survey_id, p.event_id, p.hash, p.legacy_hash,
      p.participant_email, p.participant_identifier FROM
      redcap_surveys_response AS r JOIN redcap_surveys_participants AS
      p ON r.participant_id = p.participant_id WHERE
      p.participant_email = :participant_email_1 AND p.survey_id =
      :survey_id_1

    '''
    r = redcapdb.redcap_surveys_response.alias('r')
    p = redcapdb.redcap_surveys_participants.alias('p')
    return r.join(p, r.c.participant_id == p.c.participant_id).select().where(
            and_(p.c.participant_email == mail, p.c.survey_id == survey_id))


class NoPermission(TypeError):
    def __init__(self, whynot):
        self.whynot = whynot

    def __str__(self):
        return '%s(%s)' % (self.__class__.__name__, self.whynot)


class NotDROC(TypeError):
    pass


class Affiliate(Token):
    def __init__(self, badge, query, saa_rc):
        self.badge = badge
        self.__saa_rc = saa_rc
        self.__query = query

    def __repr__(self):
        return 'Affiliate(%s)' % (self.badge.cn)

    def ensure_saa_survey(self, ttl=timedelta(seconds=15)):
        # TODO: redcap_connect should use notarized badges rather
        # than raw cn
        badge = self.badge

        def _ensure():
            fields = dict(user_id=badge.cn,
                          full_name=badge.sort_name())
            return (ttl, self.__saa_rc(badge.cn, fields))

        return self.__query(('SAA', badge.cn), _ensure, 'SAA link')


class InvestigatorRequest(Token):
    '''Power to file authenticated oversight requests.
    '''
    def __init__(self, badge, browser, orc):
        self.__badge = badge
        self.__orc = orc
        self.__browser = browser

    def __repr__(self):
        return '%s(from=%s)' % (self.__class__.__name__, self.__badge.cn)

    def ensure_oversight_survey(self, uids, what_for):
        if what_for not in HeronRecords.oversight_request_purposes:
            raise TypeError(what_for)

        tp = team_params(self.__browser.lookup, uids)

        return self.__orc(
            self.__badge.cn, dict(tp,
                                  user_id=self.__badge.cn,
                                  full_name=self.__badge.sort_name(),
                                  what_for=what_for,
                                  multi='yes'), multi=True)


def team_params(lookup, uids):
    r'''
    >>> import pprint
    >>> (mc, ) = medcenter.Mock.make([medcenter.MedCenter])
    >>> pprint.pprint(list(team_params(mc.peer_badge,
    ...                                ['john.smith', 'bill.student'])))
    ... # doctest: +ELLIPSIS
    [('user_id_1', 'john.smith'),
     ('name_etc_1', 'Smith, John\nChair of Department of Neur...'),
     ('user_id_2', 'bill.student'),
     ('name_etc_2', 'Student, Bill\nStudent\nUndergrad')]

    '''
    nested = [[('user_id_%d' % (i + 1), uid),
               ('name_etc_%d' % (i + 1), '%s, %s\n%s\n%s' % (
                    a.sn, a.givenname, a.title or '', a.ou or ''))]
              for (i, uid, a) in
              [(i, uids[i], lookup(uids[i]))
               for i in range(0, len(uids))]]
    return itertools.chain.from_iterable(nested)


class Mock(injector.Module, rtconfig.MockMixin):
    def __init__(self):
        injector.Module.__init__(self)
        token = redcap_connect._test_settings.token
        webcap = redcap_connect._MockREDCapAPI()
        self.__redcapapi = redcap_connect.EndPoint(webcap, token)

    @singleton
    @provides((redcap_connect.SurveySetup, SAA_CONFIG_SECTION))
    def _rc_saa(self):
        opts = redcap_connect._test_settings
        return redcap_connect.SurveySetup(opts, self.__redcapapi,
                                          survey_id=opts.survey_id)

    @singleton
    @provides((redcap_connect.SurveySetup, OVERSIGHT_CONFIG_SECTION))
    def _rc_oversight(self):
        opts = redcap_connect._test_settings
        return redcap_connect.SurveySetup(opts, self.__redcapapi,
                                          project_id=opts.project_id,
                                          executives=['big.wig'])

    @provides(disclaimer.KBadgeInspector)
    @inject(mc=medcenter.MedCenter)
    def notary(self, mc):
        return mc.getInspector()

    @classmethod
    def mods(cls):
        log.debug('heron_policy.Mock.mods')
        return ([im
                 for m in (medcenter, i2b2pm, disclaimer,
                           redcapdb, noticelog)
                 for im in m.Mock.mods()] + [cls()])


def mock_context(who, depgraph=None):
    from pyramid.testing import DummyRequest
    context = medcenter.AttrDict()
    req = DummyRequest(context=context)
    if not depgraph:
        depgraph, = Mock.make([None])
    (mc, hp) = depgraph.get(medcenter.MedCenter), depgraph.get(HeronRecords)
    mc.authenticated(who, req)
    return hp, context, req


class RunTime(rtconfig.IniModule):  # pragma nocover
    @singleton
    @provides(rtconfig.Clock)
    def _real_time(self):
        import datetime
        return datetime.datetime

    @singleton
    @provides((redcap_connect.SurveySetup, SAA_CONFIG_SECTION))
    def _rc_saa(self):
        opts, api = redcap_connect.RunTime.endpoint(self, SAA_CONFIG_SECTION)
        return redcap_connect.SurveySetup(opts, api, survey_id=opts.survey_id)

    @singleton
    @provides((redcap_connect.SurveySetup, OVERSIGHT_CONFIG_SECTION))
    def _rc_oversight(self):
        opts, api = redcap_connect.RunTime.endpoint(
            self, OVERSIGHT_CONFIG_SECTION, extra=('project_id',))
        return redcap_connect.SurveySetup(
            opts, api,
            project_id=opts.project_id)

    @provides(disclaimer.KBadgeInspector)
    @inject(mc=medcenter.MedCenter)
    def notary(self, mc):
        return mc.getInspector()

    @classmethod
    def mods(cls, ini):
        return ([im for m in
                 (medcenter,
                  i2b2pm,
                  disclaimer,
                  noticelog)
                 for im in m.RunTime.mods(ini)] + [cls(ini)])


def _integration_test():  # pragma nocover
    import sys

    if '--doctest' in sys.argv:
        import doctest
        doctest.testmod()

    logging.basicConfig(level=logging.DEBUG, stream=sys.stderr)

    userid = sys.argv[1]
    req = medcenter.MockRequest()
    req.remote_user = userid
    mc, hr = RunTime.make(None, [medcenter.MedCenter, HeronRecords])
    mc.authenticated(userid, req)
    hr.grant(req.context, PERM_STATUS)
    print req.context.status

    hr.grant(req.context, PERM_START_I2B2)
    print req.context.start_i2b2()

if __name__ == '__main__':  # pragma nocover
    _integration_test()
