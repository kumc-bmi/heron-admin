'''heron_policy.py -- HERON policy decisions, records
-----------------------------------------------------

:class:`HeronRecords` implements the `HERON governance`__ policies.

__ http://informatics.kumc.edu/work/wiki/HERON#governance

.. For debugging, change .. to >>>.
.. logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)

View-only access for Qualified Faculty
======================================

Excerpting from `HERON training materials`__:

  For qualified faculty who want view-only access to do patient count
  queries, executing a system access agreement is the only
  requirement.

__ http://informatics.kumc.edu/work/wiki/HERONTrainingMaterials

  >>> hp, mc, dr, oc = Mock.make((HeronRecords, medcenter.MedCenter,
  ...                             DecisionRecords, OversightCommittee))

Recalling the login protocol from :mod:`heron_wsgi.cas_auth`::

  >>> def _login(uid, mc, hp):
  ...     req = medcenter.MockRequest()
  ...     mc.issue(uid, req)
  ...     hp.issue(uid, req)
  ...     return req

When a qualified faculty member from our mock directory logs in,
they will be able to make investigator requests::

  >>> facreq = _login('john.smith', mc, hp)
  >>> hp.investigator_request(facreq.badge)
  InvestigatorRequest(from=john.smith)

  >>> hp.audit_all([facreq.badge], PERM_INVESTIGATOR)


John has signed the system access agreement and is current on his
human subjects training, so he can access the repository::

  >>> hp.repository_authz(facreq.badge)
  Access(John Smith <john.smith@js.example>)


Unforgeable System Access Agreement
***********************************

:meth:`HeronRecords.issue` also issues an :class:`Affiliate` user
capability, which provides a link to an authenticated system access
survey, using :mod:`heron_wsgi.admin_lib.redcap_connect`::

  >>> facreq.affiliate.ensure_saa_survey().split('?')
  ... # doctest: +NORMALIZE_WHITESPACE
  ['http://bmidev1/redcap-host/surveys/',
   's=f1f9&full_name=Smith%2C+John&user_id=john.smith']

Sponsored Users
===============

Bill cannot access the HERON repository because he is neither
faculty not sponsored::

  >>> stureq = _login('bill.student', mc, hp)
  >>> stureq.affiliate
  Affiliate(bill.student)
  >>> hp.repository_authz(stureq.badge)
  Traceback (most recent call last):
    ...
  NotSponsored

.. note:: We count on sqlalchemy to recover from errors in the connection
   to the database of sponsorship records.

Nor has he completed human subjects training::

  >>> stureq.affiliate.training()
  Traceback (most recent call last):
  ...
  NoTraining

Another student has been sponsored and is current on training, but has
not yet executed the system access agreement::

  >>> stu2req = _login('some.one', mc, hp)
  >>> stu2req.affiliate
  Affiliate(some.one)
  >>> stu2req.affiliate.sponsor() == True
  True
  >>> stu2req.affiliate.training()
  '2012-01-01'
  >>> hp.repository_authz(stu2req.badge)
  Traceback (most recent call last):
  ...
  NoAgreement

.. todo:: secure represention of sponsor rather than True/False?


Exception for executives from participating instituions
=======================================================

Executives don't need sponsorship::

  >>> exreq = _login('big.wig', mc, hp)
  >>> exreq.affiliate
  Affiliate(big.wig)
  >>> hp.repository_authz(exreq.badge)
  Access(Big Wig <big.wig@js.example>)

Sponsorship and data usage requests to the oversight committee
==============================================================

Faculty and executives can make sponsorship and data usage requests to
the oversight committee::

  >>> facreq.agent.oversight_request().ensure_oversight_survey(
  ...        ['some.one'], what_for=HeronRecords.DATA_USE).split('&')
  ... # doctest: +NORMALIZE_WHITESPACE
  ['http://bmidev1/redcap-host/surveys/?s=f1f9',
   'full_name=Smith%2C+John',
   'multi=yes',
   'name_etc_1=One%2C+Some%0A%0A',
   'user_id=john.smith',
   'user_id_1=some.one',
   'what_for=2']


  >>> ok = exreq.agent.oversight_request().ensure_oversight_survey(
  ...        ['some.one'], what_for=HeronRecords.DATA_USE).split('&')


Directory Search for Team Members
*********************************

Part of making oversight requests is nominating team members::

  >>> facreq.agent.browser.lookup('some.one')
  Some One <some.one@js.example>
  >>> facreq.agent.browser.search(5, 'john.smith', '', '')
  [John Smith <john.smith@js.example>]


Notification of Oversight Decisions
***********************************

What decision notifications are pending?

  >>> ds = dr.oversight_decisions()
  >>> ds  # doctest: +NORMALIZE_WHITESPACE
  [(34, u'-565402122873664774', u'2', 3),
   (34, u'23180811818680005', u'1', 3),
   (34, u'6373469799195807417', u'1', 3)]

Get details that we might want to use in composing the notification::

  >>> from pprint import pprint
  >>> for pid, record, decision, qty in ds:
  ...    pprint(dr.decision_detail(record))
  (John Smith <john.smith@js.example>,
   [Bill Student <bill.student@js.example>],
   {u'approve_kuh': u'2',
    u'approve_kumc': u'2',
    u'approve_kupi': u'2',
    u'date_of_expiration': u'',
    u'full_name': u'John Smith',
    u'project_title': u'Cart Blanche',
    u'user_id': u'john.smith',
    u'user_id_1': u'bill.student'})
  (John Smith <john.smith@js.example>,
   [Bill Student <bill.student@js.example>],
   {u'approve_kuh': u'1',
    u'approve_kumc': u'1',
    u'approve_kupi': u'1',
    u'date_of_expiration': u'1950-02-27',
    u'full_name': u'John Smith',
    u'project_title': u'Cure Polio',
    u'user_id': u'john.smith',
    u'user_id_1': u'bill.student'})
  (John Smith <john.smith@js.example>,
   [Some One <some.one@js.example>, Carol Student <carol.student@js.example>],
   {u'approve_kuh': u'1',
    u'approve_kumc': u'1',
    u'approve_kupi': u'1',
    u'date_of_expiration': u'',
    u'full_name': u'John Smith',
    u'project_title': u'Cure Warts',
    u'user_id': u'john.smith',
    u'user_id_1': u'some.one',
    u'user_id_2': u'carol.student'})

.. todo:: consider factoring out low level details to make
          the policy more clear as code.


Overight Auditing
=================

Oversight committee members can get sensitive audit info::

.. todo: get these test working again

  ### oc.issue(exreq)
  [I2B2SensitiveUsage()]

Ordinary users cannot, though they can get aggregate usage info::

  ### oc.issue(stureq)
  []
  >>> stureq.stats_reporter
  I2B2AggregateUsage()


Disclaimers
===========

TODO.

  >>> raise NotImplementedError

'''

from datetime import timedelta
import itertools
import logging
import csv  # csv, os only used _DataDict, i.e. testing
import os

import injector
from injector import inject, provides, singleton
from sqlalchemy import orm, engine
from sqlalchemy.sql import select, and_, func

from ocap_file import Token
import notary
import rtconfig
import i2b2pm
import medcenter
import redcap_connect
import redcapdb
import noticelog
import disclaimer
from disclaimer import Disclaimer, Acknowledgement, KTimeSource
from audit_usage import I2B2AggregateUsage, I2B2SensitiveUsage
from cache_remote import Cache

SAA_CONFIG_SECTION = 'saa_survey'
OVERSIGHT_CONFIG_SECTION = 'oversight_survey'
PERM_INVESTIGATOR = 'investigator'
# todo: consider a mysql session store for capabilities
PERM_DROC = __name__ + '.droc'

log = logging.getLogger(__name__)


class OversightCommittee(Token, Cache):
    @inject(redcap_sessionmaker=(orm.session.Session,
                                 redcapdb.CONFIG_SECTION),
            oversight_rc=(redcap_connect.SurveySetup,
                          OVERSIGHT_CONFIG_SECTION),
            mc=medcenter.MedCenter,
            auditor=I2B2SensitiveUsage)
    def __init__(self, redcap_sessionmaker, oversight_rc, mc, auditor):
        self.__rcsm = redcap_sessionmaker
        self.project_id = oversight_rc.project_id
        self.__mc = mc
        self.inspector = mc.getInspector()
        self.__auditor = auditor

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

    def droc_auditor(self, alleged_badge,
                     ttl=timedelta(seconds=60)):
        badge = self.inspector.vouch(alleged_badge)

        def db_q():
            s = self.__rcsm()
            ans = s.execute(self._memberq(self.project_id, badge.cn))

            in_droc = len(ans.fetchall()) == 1
            log.info('issue DROC? %s', in_droc)
            return ttl, in_droc

        in_droc = self._query(badge.cn, db_q)
        if not in_droc:
            raise NotDROC

        return self.__auditor


class HeronRecords(Token):
    '''

    In the oversight_project, userid of sponsored users are stored in
    REDCap fields with names like user_id_% and approval decisions are
    stored in fields with names like approve_%, with a distinct
    approve_% field for each participating institution.

    >>> ddict = _DataDict('oversight')
    >>> dd_orgs = [n[len('approve_'):] for (n, etc) in ddict.fields()
    ...            if n.startswith('approve_')]
    >>> set(dd_orgs) == set(HeronRecords.institutions)
    True

    >>> len([n for (n, etc) in ddict.fields() if n.startswith('user_id_')]) > 3
    True


    >>> uses = ddict.radio('what_for')
    >>> HeronRecords.oversight_request_purposes == tuple(
    ...     [ix for (ix, label) in uses])
    True

    .. todo:: check expiration date
    '''
    permissions = (PERM_INVESTIGATOR, PERM_DROC)
    institutions = ('kuh', 'kupi', 'kumc')

    SPONSORSHIP = '1'
    DATA_USE = '2'
    oversight_request_purposes = (SPONSORSHIP, DATA_USE)

    @inject(mc=medcenter.MedCenter,
            pm=i2b2pm.I2B2PM,
            stats=I2B2AggregateUsage,
            saa_rc=(redcap_connect.SurveySetup,
                    SAA_CONFIG_SECTION),
            oversight_rc=(redcap_connect.SurveySetup,
                          OVERSIGHT_CONFIG_SECTION),
            oc=OversightCommittee,
            smaker=(orm.session.Session,
                    redcapdb.CONFIG_SECTION),
            timesrc=KTimeSource)
    def __init__(self, mc, pm, stats, saa_rc, oversight_rc, oc,
                 smaker, timesrc):
        log.debug('HeronRecords.__init__ again?')
        self._smaker = smaker
        self._mc = mc
        self._pm = pm
        self.__stats = stats
        self._t = timesrc
        self._saa_survey_id = saa_rc.survey_id
        self._saa_rc = saa_rc
        self._oversight_rc = oversight_rc
        self.__oc = oc
        self._oversight_project_id = oversight_rc.project_id
        self._executives = oversight_rc.executives

    def issue(self, uid, req):
        req.stats_reporter = self.__stats

        req.affiliate = Affiliate(req.badge,
                                  self._t,
                                  self._saa_rc,
                                  self._check_saa_signed,
                                  self._sponsored)
        return [req.stats_reporter, req.affiliate]

    def audit_all(self, caps, p):
        log.debug('HeronRecords.audit(%s, %s)' % (caps, p))

        if p is PERM_INVESTIGATOR:
            for cap in caps:
                try:
                    self.investigator_request(cap)
                    return
                except (medcenter.NotFaculty, notary.NotVouchable):
                    pass
        elif p is PERM_DROC:
            for cap in caps:
                try:
                    self.__oc.droc_auditor(cap)
                except (NoPermission, notary.NotVouchable):
                    pass

        raise TypeError

    def repository_authz(self, alleged_badge):
        badge = self._mc.getInspector().vouch(alleged_badge)

        try:
            self.investigator_request(badge)
        except medcenter.NotFaculty:
            self._sponsored(badge.cn)
        self._training_current(badge)
        self._check_saa_signed(badge.mail)

        return self._pm.account_for(badge)

    def _sponsored(self, uid):
        decision, candidate, dc = _sponsor_queries(self._oversight_project_id)

        # mysql work-around for
        # 1248, 'Every derived table must have its own alias'
        dc = dc.alias('mw')
        q = dc.select(and_(dc.c.candidate == uid,
                           dc.c.decision == DecisionRecords.YES))

        for ans in self._smaker().execute(q).fetchall():
            if ans.dt_exp <= '' or self._t.today().isoformat() <= ans.dt_exp:
                log.info('sponsorship OK: %s', ans)
                return True

        log.info('not sponsored: %s', uid)
        raise NotSponsored()

    def _training_current(self, badge):
        try:
            when = self._mc.trained_thru(badge)
        except (IOError):
            log.warn('failed to look up training due to IOError')
            log.debug('training error detail', exc_info=True)
            raise NoTraining
        except LookupError:
            log.info('no training on file for: %s (%s)',
                     self.cn, self.full_name())
            raise NoTraining

        current = when >= self._t.today().isoformat()
        if not current:
            log.info('training expried %s for: %s (%s)',
                     when, self.cn, self.full_name())
            raise NoTraining(when)

    def _check_saa_signed(self, mail):
        '''Test for an authenticated SAA survey response.

        todo: cache results
        '''
        if not self._smaker().execute(_saa_query(mail, self._saa_survey_id)).\
                fetchall():
            log.info('no SAA: %s', mail)
            raise NoAgreement
        return True

    def investigator_request(self, badge):
        mc = self._mc

        fac = mc.is_faculty(badge)
        ex = badge.cn in self._executives
        log.info('investigator_request: %s faculty? %s executive? %s',
                 badge, fac, ex)

        if not (fac or ex):
            raise medcenter.NotFaculty

        return InvestigatorRequest(badge, mc.peer_badge, self.__oc)


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


def _sponsor_queries(oversight_project_id):
    '''
      >>> from pprint import pprint
      >>> decision, candidate, cdwho = _sponsor_queries(123)

      >>> print str(decision)
      ...  # doctest: +NORMALIZE_WHITESPACE
      SELECT redcap_data.project_id, redcap_data.record,
      redcap_data.value AS decision, count(*) AS count_1 FROM
      redcap_data WHERE redcap_data.field_name LIKE :field_name_1 AND
      redcap_data.project_id = :project_id_1 GROUP BY
      redcap_data.project_id, redcap_data.record, redcap_data.value
      HAVING count(*) = :count_2

      >>> pprint(decision.compile().params)
      {u'count_2': 3, u'field_name_1': 'approve_%', u'project_id_1': 123}


      >>> print str(candidate)
      ...  # doctest: +NORMALIZE_WHITESPACE
      SELECT redcap_data.project_id, redcap_data.record,
      redcap_data.value AS userid FROM redcap_data WHERE
      redcap_data.field_name LIKE :field_name_1

      >>> pprint(candidate.compile().params)
      {u'field_name_1': 'user_id_%'}

      >>> print str(cdwho) # doctest: +NORMALIZE_WHITESPACE
      SELECT cd_record AS record,
             cd_decision AS decision,
             who_userid AS candidate,
             expire_dt_exp AS dt_exp
      FROM
        (SELECT cd.project_id AS cd_project_id,
                cd.record AS cd_record,
                cd.decision AS cd_decision,
                cd.count_1 AS cd_count_1,
                who.project_id AS who_project_id,
                who.record AS who_record,
                who.userid AS who_userid,
                expire.project_id AS expire_project_id,
                expire.record AS expire_record,
                expire.dt_exp AS expire_dt_exp
         FROM
           (SELECT redcap_data.project_id AS project_id,
                   redcap_data.record AS record,
                   redcap_data.value AS decision, count(*) AS count_1
            FROM redcap_data
            WHERE redcap_data.field_name LIKE :field_name_1
              AND redcap_data.project_id = :project_id_1
            GROUP BY redcap_data.project_id, redcap_data.record,
                     redcap_data.value
            HAVING count(*) = :count_2) AS cd
           JOIN
             (SELECT redcap_data.project_id AS project_id,
                     redcap_data.record AS record,
                     redcap_data.value AS userid
              FROM redcap_data
              WHERE redcap_data.field_name LIKE :field_name_2) AS who
           ON who.record = cd.record
           AND who.project_id = cd.project_id
           LEFT OUTER JOIN (SELECT redcap_data.project_id AS project_id,
                                   redcap_data.record AS record,
                                   redcap_data.value AS dt_exp
                            FROM redcap_data
                            WHERE redcap_data.field_name = :field_name_3)
                             AS expire
           ON expire.record = cd.record AND expire.project_id = cd.project_id)
              AS cdwho

      >>> pprint(cdwho.compile().params)
      {u'count_2': 3,
       u'field_name_1': 'approve_%',
       u'field_name_2': 'user_id_%',
       u'field_name_3': 'date_of_expiration',
       u'project_id_1': 123}

    '''
    # grumble... sql in python clothing
    # but for this price, we can run it on sqlite for testing as well as mysql
    # and sqlalchemy will take care of the bind parameter syntax
    rd = redcapdb.redcap_data

    # committee decisions
    decision = select((rd.c.project_id, rd.c.record,
                       rd.c.value.label('decision'),
                       func.count())).where(
        and_(rd.c.field_name.like('approve_%'),
             rd.c.project_id == oversight_project_id)).\
             group_by(rd.c.project_id,
                      rd.c.record,
                      rd.c.value).having(
                 func.count() == len(HeronRecords.institutions)).alias('cd')

    # todo: consider combining record, event, project_id into one attr
    candidate = select((rd.c.project_id, rd.c.record,
                        rd.c.value.label('userid'))).where(
        rd.c.field_name.like('user_id_%')).alias('who')

    dt_exp = select((rd.c.project_id, rd.c.record,
                    rd.c.value.label('dt_exp'))).where(
        rd.c.field_name == 'date_of_expiration').alias('expire')

    j = decision.join(candidate,
                      and_(candidate.c.record == decision.c.record,
                           candidate.c.project_id == decision.c.project_id)).\
                           outerjoin(dt_exp, and_(
            dt_exp.c.record == decision.c.record,
            dt_exp.c.project_id == decision.c.project_id)).\
            alias('cdwho').select()

    cdwho = j.with_only_columns((j.c.cd_record.label('record'),
                                 j.c.cd_decision.label('decision'),
                                 j.c.who_userid.label('candidate'),
                                 j.c.expire_dt_exp.label('dt_exp')))

    return decision, candidate, cdwho


class NoPermission(Exception):
    pass


class NotSponsored(NoPermission):
    pass


class NoTraining(NoPermission):
    def __init__(self, when=None):
        self.when = when


class NoAgreement(NoPermission):
    pass


class NotDROC(NoPermission):
    pass


class Affiliate(Token, Cache):
    def __init__(self, badge, timesrc, saa_rc, check_sig, sponsored):
        Cache.__init__(self, timesrc.now)
        self.badge = badge
        self.__saa_rc = saa_rc
        self.__check_sig = check_sig
        self.__sponsored = sponsored

    def __repr__(self):
        return 'Affiliate(%s)' % (self.badge.cn)

    def ensure_saa_survey(self, ttl=timedelta(seconds=15)):
        def _ensure():
            fields = dict(user_id=self.badge.cn,
                          full_name=self.badge.sort_name())
            return (ttl, self.__saa_rc(self.badge.cn, fields))

        return self._query('sa', _ensure)

    def signature(self, ttl=timedelta(seconds=15)):
        def _sig():
            return (ttl, int(self.__check_sig(self.badge.mail)))
        return self._query('sig', _sig)

    def sponsor(self, ttl=timedelta(seconds=60)):
        return self._query('sponsored',
                           lambda: (ttl,
                                    int(self.__sponsored(self.badge.cn))))

    def disclaimer_ack(self):
        raise NotImplementedError
        return self._hr._disclaimer_acknowledgement(self.__cn)


class InvestigatorRequest(Token):
    '''Power to file authenticated oversight requests.
    '''
    def __init__(self, badge, lookup, orc):
        self.__badge = badge
        self.__orc = orc
        self.__lookup = lookup

    def __repr__(self):
        return '%s(from=%s)' % (self.__class__.__name__, self.__badge.cn)

    def ensure_oversight_survey(self, uids, what_for):
        if what_for not in HeronRecords.oversight_request_purposes:
            raise TypeError(what_for)

        tp = team_params(self.__lookup, uids)

        return self.__orc(
            self.__agent.cn, dict(tp,
                                  user_id=self.__agent.cn,
                                  full_name=self.__agent.sort_name(),
                                  what_for=what_for,
                                  multi='yes'), multi=True)


def team_params(lookup, uids):
    r'''
    >>> import pprint
    >>> (mc, ) = medcenter.Mock.make([medcenter.MedCenter])
    >>> pprint.pprint(list(team_params(mc.lookup,
    ...                                ['john.smith', 'bill.student'])))
    [('user_id_1', 'john.smith'),
     ('name_etc_1', 'Smith, John\nChair of Department of Neurology\nNeurology'),
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


class DecisionRecords(object):
    '''

    .. note:: At test time, let's check consistency with the data
              dictionary.

    >>> choices = dict(_DataDict('oversight').radio('approve_kuh'))
    >>> choices[DecisionRecords.YES]
    'Yes'
    >>> choices[DecisionRecords.NO]
    'No'
    >>> len(choices)
    3

    '''

    YES = '1'
    NO = '2'

    @inject(orc=(redcap_connect.SurveySetup, OVERSIGHT_CONFIG_SECTION),
            smaker=(orm.session.Session, redcapdb.CONFIG_SECTION),
            mc=medcenter.MedCenter)
    def __init__(self, orc, smaker, mc):
        self._oversight_project_id = orc.project_id
        self._mc = mc
        self._smaker = smaker

    def oversight_decisions(self):
        '''In order to facilitate email notification of committee
        decisions, find decisions where notification has not been sent.
        '''
        cd, who, cdwho = _sponsor_queries(self._oversight_project_id)

        # decisions without notifications
        nl = noticelog.notice_log
        dwn = cd.outerjoin(nl).select() \
            .with_only_columns(cd.columns).where(nl.c.record == None)
        return self._smaker().execute(dwn).fetchall()

    def decision_detail(self, record):
        avl = list(redcapdb.allfields(self._smaker(),
                                      self._oversight_project_id,
                                      record))
        mc = self._mc
        team = [mc.lookup(user_id)
                for user_id in
                [v for a, v in avl if v and a.startswith('user_id_')]]

        d = dict(avl)
        investigator = mc.lookup(d['user_id'])
        return investigator, team, d


class _DataDict(object):
    '''
    .. todo:: use pkg_resources rather than os to get redcap_dd
    '''
    def __init__(self, name,
                 base=os.path.join(os.path.dirname(__file__),
                                   '..', 'redcap_dd')):
        def open_it():
            return open(os.path.join(base, name + '.csv'))
        self._open = open_it

    def fields(self):
        rows = csv.DictReader(self._open())
        for row in rows:
            yield row["Variable / Field Name"], row

    def radio(self, field_name):
        for n, row in self.fields():
            if n == field_name:
                choicetxt = row["Choices, Calculations, OR Slider Labels"]
                break
        else:
            raise KeyError
        return [tuple(choice.strip().split(", ", 1))
                for choice in choicetxt.split('|')]


class TestSetUp(disclaimer.TestSetUp):
    oversight_pid = redcap_connect._test_settings.project_id
    saa_sid = redcap_connect._test_settings.survey_id

    @singleton
    @provides((orm.session.Session, redcapdb.CONFIG_SECTION))
    @inject(engine=(engine.base.Connectable,
                    redcapdb.CONFIG_SECTION),
            timesrc=KTimeSource)
    def redcap_sessionmaker(self, engine, timesrc):
        from redcapdb import add_test_eav

        smaker = super(TestSetUp, self).redcap_sessionmaker(engine=engine)
        s = smaker()

        def add_oversight_request(user_id, full_name, project_title,
                                  candidates, reviews,
                                  date_of_expiration=''):
            # e/a/v = entity/attribute/value
            e = hash((user_id, project_title))
            add_test_eav(s, self.oversight_pid, 1, e,
                         (('user_id', user_id),
                          ('full_name', full_name),
                          ('project_title', project_title),
                          ('date_of_expiration', date_of_expiration)))
            add_test_eav(s, self.oversight_pid, 1, e,
                         [('user_id_%d' % n, userid)
                          for n, userid in candidates])
            add_test_eav(s, self.oversight_pid, 1, e,
                         [('approve_%s' % org, decision)
                          for org, decision in reviews])

        # approve 2 users in 1 request
        add_oversight_request('john.smith', 'John Smith', 'Cure Warts',
                              ((1, 'some.one'), (2, 'carol.student')),
                              [(org, DecisionRecords.YES)
                               for org in HeronRecords.institutions])

        # A request to sponsor bill.student is only reviewed by 2 of 3 orgs:
        add_oversight_request('john.smith', 'John Smith', 'Cure Hair Loss',
                              ((1, 'bill.student'),),
                              [(org, DecisionRecords.YES)
                               for org in HeronRecords.institutions[:2]])

        # Another request to sponsor bill.student was rejected:
        add_oversight_request('john.smith', 'John Smith', 'Cart Blanche',
                              ((1, 'bill.student'),),
                              [(org, DecisionRecords.NO)
                               for org in HeronRecords.institutions])

        # Another request has expired:
        add_oversight_request('john.smith', 'John Smith', 'Cure Polio',
                              ((1, 'bill.student'),),
                              [(org, DecisionRecords.YES)
                               for org in HeronRecords.institutions],
                              '1950-02-27')

        log.debug('add SAA records')
        redcapdb.redcap_surveys_participants.create(s.bind)
        s.commit()
        redcapdb.redcap_surveys_response.create(s.bind)
        noticelog.notice_log.schema = None  # sqlite doesn't grok schemas
        noticelog.notice_log.create(s.bind)
        for email in ['john.smith@js.example', 'big.wig@js.example']:
            s.execute(redcapdb.redcap_surveys_participants.insert().values(
                    participant_id=abs(hash(email)),
                    survey_id=self.saa_sid, participant_email=email))
            s.execute(redcapdb.redcap_surveys_response.insert().values(
                    response_id=abs(hash(email)), record=abs(hash(email)),
                    completion_time=timesrc.today() + \
                        timedelta(days=-7),
                    participant_id=abs(hash(email))))

        def add_droc_member(u, p):
            log.debug('add DROC member: %s to project %s', u, p)
            urt = redcapdb.redcap_user_rights
            s.execute(urt.insert().values(project_id=p, username=u))
        add_droc_member('big.wig', self.oversight_pid)

        s.commit()
        return smaker


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

    @classmethod
    def mods(cls):
        log.debug('heron_policy.Mock.mods')
        return (medcenter.Mock.mods() + i2b2pm.Mock.mods()
                + disclaimer.Mock.mods() + [TestSetUp(), cls()])


class RunTime(rtconfig.IniModule):  # pragma nocover
    @singleton
    @provides(KTimeSource)
    def _timesrc(self):
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
            self, OVERSIGHT_CONFIG_SECTION, extra=('executives', 'project_id'))
        return redcap_connect.SurveySetup(
            opts, api,
            project_id=opts.project_id,
            executives=opts.executives.split(','))

    @classmethod
    def mods(cls, ini):
        return (medcenter.RunTime.mods(ini) +
                i2b2pm.RunTime.mods(ini) +
                disclaimer.RunTime.mods(ini) +
                [cls(ini)])


def _test_main():  # pragma nocover
    import sys

    if '--doctest' in sys.argv:
        import doctest
        doctest.testmod()

    logging.basicConfig(level=logging.DEBUG, stream=sys.stderr)

    userid = sys.argv[1]
    req = medcenter.MockRequest()
    req.remote_user = userid
    hr, ds = RunTime.make(None, [HeronRecords, DecisionRecords])
    hr.issue(req)
    print "DROC auth?"
    try:
        print req.droc_audit.patient_set_queries(recent=True, small=True)
    except AttributeError:
        print "DROC auth: NO"
    print req.agent.repository_authz()

    print "pending notifications:", ds.oversight_decisions()

if __name__ == '__main__':  # pragma nocover
    _test_main()
