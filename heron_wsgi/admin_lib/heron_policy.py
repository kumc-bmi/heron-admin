'''heron_policy.py -- HERON policy decisions, records
-----------------------------------------------------

:class:`HeronRecords` implements the `HERON governance`__ policies.

__ http://informatics.kumc.edu/work/wiki/HERON#governance

  >>> logged = rtconfig._printLogs(level=logging.INFO)

View-only access for Qualified Faculty
======================================

Excerpting from `HERON training materials`__:

  For qualified faculty who want view-only access to do patient count
  queries, executing a system access agreement is the only
  requirement.

__ http://informatics.kumc.edu/work/wiki/HERONTrainingMaterials

  >>> hp, mc, oc = Mock.make((HeronRecords, medcenter.MedCenter,
  ...                         OversightCommittee))
  >>> print(logged())
  INFO:cache_remote:LDAPService@1 cache initialized
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
  >>> print(logged())
  ... # doctest: +NORMALIZE_WHITESPACE +ELLIPSIS
  INFO:cache_remote:LDAP query for ('(cn=john.smith)', ...
  INFO:cache_remote:system access query for ('SAA', 'john.smith@js.example')
  INFO:cache_remote:... cached until 2011-09-02 00:00:15.500000
  INFO:cache_remote:in DROC? query for john.smith
  INFO:cache_remote:... cached until 2011-09-02 00:01:00.500000
  >>> facreq.context.status  # doctest: +NORMALIZE_WHITESPACE
  Status(complete=True,
         current_training=Training(username='john.smith',
                                   expired='2012-01-01',
                                   completed='2012-01-01',
                                   course='Human Subjects 101'),
         droc=None, executive=False,
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
    Disclaimer(project_id=123, record=1,
               disclaimer_id=1,
               url=http://example/blog/item/heron-release-xyz, current=1)
  >>> _ = logged()
  >>> facreq.context.disclaimers.ack_disclaimer(facreq.context.badge)
  >>> facreq.context.start_i2b2()
  Access(John Smith <john.smith@js.example>)
  >>> print(logged())
  ... # doctest: +NORMALIZE_WHITESPACE +ELLIPSIS
  INFO:disclaimer:disclaimer ack:
  Acknowledgement(project_id=34, record=...,
    ack=2011-09-02 john.smith /heron-release-xyz,
    timestamp=2011-09-02 00:00:00, user_id=john.smith,
    disclaimer_address=http://example/blog/item/heron-release-xyz)
  INFO:i2b2pm:Finding I2B2 project for REDCap pids: []
  INFO:i2b2pm:User REDCap projects are not in HERON

Unforgeable System Access Agreement
***********************************

:meth:`HeronRecords.grant` also issues an :class:`Affiliate` user
capability, which provides a link to an authenticated system access
survey, using :mod:`heron_wsgi.admin_lib.redcap_connect`::

  >>> facreq = _login('john.smith', mc, hp, PERM_SIGN_SAA)
  >>> facreq.context.sign_saa.ensure_saa_survey().split('?')
  ... # doctest: +NORMALIZE_WHITESPACE
  ['http://testhost/redcap-host/surveys/',
   's=aqFVbr&full_name=Smith%2C+John&user_id=john.smith']
  >>> print(logged())
  INFO:cache_remote:SAA link query for ('SAA', 'john.smith')
  INFO:cache_remote:... cached until 2011-09-02 00:00:16.500000

Any CAS authenticated user can sign Data Usage Agreement
********************************************************

John is a team member on a study which has requested a HERON data extract.
John authenticates to the site using CAS and is presented with a link to the
HERON Data Use Agreement.

:meth:`HeronRecords.grant` also issues an :class:`Affiliate` user
capability, which provides a link to an authenticated data usage
survey, using :mod:`heron_wsgi.admin_lib.redcap_connect`::

  >>> facreq = _login('john.smith', mc, hp, PERM_SIGN_DUA)
  >>> facreq.context.sign_dua.ensure_dua_survey().split('?')
  ... # doctest: +NORMALIZE_WHITESPACE
  ['http://testhost/redcap-host/surveys/',
   's=aqFVbr&full_name=Smith%2C+John&user_id=john.smith']
  >>> _ = logged()

Sponsored Users
===============

Bill cannot access the HERON repository because he is neither
faculty not sponsored, nor has he completed human subjects training::

  >>> stureq = _login('bill.student', mc, hp, PERM_STATUS)
  >>> print(logged())
  ... # doctest: +NORMALIZE_WHITESPACE +ELLIPSIS
  INFO:cache_remote:LDAP query for ('(cn=bill.student)', ...
  INFO:cache_remote:Sponsorship query for ('sponsorship', 'bill.student')
  INFO:heron_policy:not sponsored: bill.student
  INFO:cache_remote:... cached until 2011-09-02 00:00:03.500000
  INFO:heron_policy:no training on file for: bill.student (Bill Student)
  INFO:cache_remote:system access query for ('SAA', 'bill.student@js.example')
  INFO:cache_remote:... cached until 2011-09-02 00:00:18
  INFO:cache_remote:in DROC? query for bill.student
  INFO:cache_remote:... cached until 2011-09-02 00:01:01.500000
  >>> stureq.context.status  #doctest: +NORMALIZE_WHITESPACE
  Status(complete=False,
         current_training=None, droc=None, executive=False,
         expired_training=None, faculty=False,
         sponsored=False, system_access_signed=[])

  >>> stureq = _login('bill.student', mc, hp, PERM_START_I2B2)
  ... # doctest: +NORMALIZE_WHITESPACE
  Traceback (most recent call last):
    ...
  NoPermission: NoPermission(Status(complete=False,
                                    current_training=None, droc=None,
                                    executive=False, expired_training=None,
                                    faculty=False, sponsored=False,
                                    system_access_signed=[]))

Verify that remote accesses are cached:

  >>> stureq = _login('bill.student', mc, hp, PERM_START_I2B2)
  ... # doctest: +ELLIPSIS
  Traceback (most recent call last):
    ...
  NoPermission: ...

  >>> _ = logged()

.. note:: We count on sqlalchemy to recover from errors in the connection
   to the database of sponsorship records.

Another student has been sponsored and is current on training, but has
not yet executed the system access agreement::

  >>> stu2req = _login('some.one', mc, hp, PERM_START_I2B2)
  ... #doctest: +NORMALIZE_WHITESPACE +ELLIPSIS
  Traceback (most recent call last):
    ...
  NoPermission: NoPermission(Status(complete=False,
            current_training=...,
            droc=None, executive=False,
            expired_training=None, faculty=False, sponsored=True,
            system_access_signed=[]))
   >>> _ = logged()

This student does have authorization to sign the SAA:

  >>> stu2req = _login('some.one', mc, hp, PERM_SIGN_SAA); print(logged())
  WARNING:medcenter:missing LDAP attribute ou for some.one
  WARNING:medcenter:missing LDAP attribute title for some.one
  >>> stu2req.context.sign_saa
  Affiliate(some.one)

This student's sponsor is not with KUMC anymore

  >>> stureq = _login('jill.student', mc, hp, PERM_STATUS)
  >>> print(logged())
  ... #doctest: +NORMALIZE_WHITESPACE
  INFO:cache_remote:LDAP query for ('(cn=jill.student)', ('cn', 'givenname',
       'kumcPersonFaculty', 'kumcPersonJobcode', 'mail', 'ou', 'sn', 'title'))
  INFO:cache_remote:... cached until 2011-09-02 00:00:07.500000
  INFO:cache_remote:Sponsorship query for ('sponsorship', 'jill.student')
  INFO:cache_remote:LDAP query for (u'(cn=prof.fickle)', ('cn', 'givenname',
       'kumcPersonFaculty', 'kumcPersonJobcode', 'mail', 'ou', 'sn', 'title'))
  INFO:cache_remote:... cached until 2011-09-02 00:00:08
  INFO:cache_remote:LDAP query for (u'(mail=prof.fickle@kumc.edu)',
    ('cn', 'givenname', 'kumcPersonFaculty', 'kumcPersonJobcode', 'mail', 'ou',
     'sn', 'title'))
  INFO:cache_remote:... cached until 2011-09-02 00:00:08.500000
  WARNING:heron_policy:Sponsor prof.fickle not at med center anymore.
  INFO:heron_policy:not sponsored: jill.student
  INFO:cache_remote:... cached until 2011-09-02 00:00:07.500000
  INFO:cache_remote:system access query for ('SAA', 'jill.student@js.example')
  INFO:cache_remote:... cached until 2011-09-02 00:00:22
  INFO:cache_remote:in DROC? query for jill.student
  INFO:cache_remote:... cached until 2011-09-02 00:01:03.500000

Ensure things don't go wonky in case of missing email address

  >>> facreq = _login('todd.ryan', mc, hp, PERM_STATUS)
  >>> print(logged())
  ... # doctest: +NORMALIZE_WHITESPACE
    INFO:cache_remote:LDAP query for ('(cn=todd.ryan)', ('cn', 'givenname',
       'kumcPersonFaculty', 'kumcPersonJobcode', 'mail', 'ou', 'sn', 'title'))
    INFO:cache_remote:... cached until 2011-09-02 00:00:09
    WARNING:medcenter:missing LDAP attribute mail for todd.ryan
    INFO:cache_remote:system access query for ('SAA', 'todd.ryan@js.example')
    INFO:cache_remote:... cached until 2011-09-02 00:00:22.500000
    INFO:cache_remote:in DROC? query for todd.ryan
    INFO:cache_remote:... cached until 2011-09-02 00:01:04

  >>> facreq.context.status  # doctest: +NORMALIZE_WHITESPACE
  Status(complete=False,
         current_training=Training(username='todd.ryan',
                                   expired='2012-01-01',
                                   completed='2012-01-01',
                                   course='Human Subjects 101'),
         droc=None,
         executive=False,
         expired_training=None,
         faculty=True, sponsored=None, system_access_signed=[])

Exception for executives from participating institutions
=======================================================

Executives don't need sponsorship::

  >>> exreq = _login('big.wig', mc, hp, PERM_START_I2B2)
  >>> print(logged())
  ... # doctest: +NORMALIZE_WHITESPACE
  INFO:cache_remote:LDAP query for ('(cn=big.wig)', ('cn', 'givenname',
       'kumcPersonFaculty', 'kumcPersonJobcode', 'mail', 'ou', 'sn', 'title'))
  INFO:cache_remote:... cached until 2011-09-02 00:00:09.500000
  INFO:cache_remote:system access query for ('SAA', 'big.wig@js.example')
  INFO:cache_remote:... cached until 2011-09-02 00:00:23
  INFO:cache_remote:in DROC? query for big.wig
  INFO:cache_remote:... cached until 2011-09-02 00:01:04.500000

Oversight Requests
==================

Faculty and executives can make sponsorship and data usage requests to
the oversight committee::

  >>> facreq = _login('john.smith', mc, hp, PERM_OVERSIGHT_REQUEST)
  >>> print(logged())
  ... # doctest: +NORMALIZE_WHITESPACE
  INFO:cache_remote:LDAP query for ('(cn=john.smith)', ('cn', 'givenname',
       'kumcPersonFaculty', 'kumcPersonJobcode', 'mail', 'ou', 'sn', 'title'))
  INFO:cache_remote:... cached until 2011-09-02 00:00:10
  >>> facreq.context.oversight_request
  OversightRequest(from=john.smith)

  >>> facreq.context.oversight_request.ensure_oversight_survey(
  ...        ['some.one'], 'john.smith',
  ...        what_for=HeronRecords.DATA_USE).split('&')
  ... # doctest: +NORMALIZE_WHITESPACE
  ['http://testhost/redcap-host/surveys/?s=akvfqA',
   'faculty_email=john.smith%40js.example', 'faculty_name=Smith%2C+John',
   'full_name=Smith%2C+John',
   'multi=yes',
   'name_etc_1=One%2C+Some%0A%0A',
   'request_from_faculty=1',
   'team_email_1=some.one%40js.example',
   'user_id=john.smith',
   'user_id_1=some.one',
   'what_for=2']


  >>> exreq = _login('big.wig', mc, hp, PERM_OVERSIGHT_REQUEST)
  >>> ok = exreq.context.oversight_request.ensure_oversight_survey(
  ...        ['some.one'], 'big.wig',
  ...        what_for=HeronRecords.DATA_USE).split('&')

Students can make oversight requests, provided they indicate a faculty
sponsor:

  >>> stureq = _login('bill.student', mc, hp, PERM_OVERSIGHT_REQUEST)
  >>> stureq.context.oversight_request.ensure_oversight_survey(
  ...        ['john.smith', 'bill.student'], 'john.smith',
  ...        what_for=HeronRecords.SPONSORSHIP).split('&')
  ... # doctest: +NORMALIZE_WHITESPACE
  ['http://testhost/redcap-host/surveys/?s=43',
   'faculty_email=john.smith%40js.example', 'faculty_name=Smith%2C+John',
   'full_name=Student%2C+Bill', 'multi=yes',
   'name_etc_1=Smith%2C+John%0AChair+of+Neurology%0ANeurology',
   'name_etc_2=Student%2C+Bill%0AStudent%0AUndergrad',
   'request_from_faculty=0',
   'team_email_1=john.smith%40js.example',
   'team_email_2=bill.student%40js.example',
   'user_id=bill.student', 'user_id_1=john.smith', 'user_id_2=bill.student',
   'what_for=1']


Oversight Auditing
==================

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


Mismatch between LDAP email and CAS username
============================================

Email addresses are not limited to correspond to user ids:

  >>> reqtm = _login('trouble.maker', mc, hp, PERM_STATUS)
  >>> reqtm.context.badge
  Trouble Maker <tmaker@not.js.example>

  >>> reqtm.context.status.system_access_signed
  [datetime.datetime(2015, 11, 16, 21, 41, 1)]

'''

from __future__ import print_function
from datetime import timedelta
import itertools
import logging
from collections import namedtuple

import injector
from injector import inject, provides, singleton
from sqlalchemy import orm
from sqlalchemy.engine.base import Connectable

from ocap_file import Token, Path
import rtconfig
import i2b2pm
import medcenter
import redcap_connect
import redcap_invite
import redcapdb
import noticelog
from noticelog import OVERSIGHT_CONFIG_SECTION
import disclaimer
from audit_usage import I2B2AggregateUsage, I2B2SensitiveUsage
from cache_remote import Cache

SAA_CONFIG_SECTION = 'saa_survey'
DUA_CONFIG_SECTION = 'dua_survey'

PERM_STATUS = __name__ + '.status'
PERM_SIGN_SAA = __name__ + '.sign_saa'
PERM_SIGN_DUA = __name__ + '.sign_dua'
PERM_OVERSIGHT_REQUEST = __name__ + '.oversight_request'
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
        >>> print(OversightCommittee._memberq(238, 'big.wig'))
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
                                complete=0,
                                droc=0,
                                current_training=0, expired_training=0,
                                system_access_signed=0).keys()))


class HeronRecords(Token, Cache):
    '''In the oversight_project, userid of sponsored users are stored in
    REDCap fields with names like ... ::

    >>> ddict = noticelog.DecisionRecords.redcap_dd
    >>> [n for (n, etc) in ddict.fields() if n.startswith('user_id_')]
    ... # doctest: +ELLIPSIS
    ['user_id_1', 'user_id_2', 'user_id_3', ...]

    Approval decisions are stored in one field per participating
    institution::

    >>> sorted(n for (n, etc) in ddict.fields() if n.startswith('approve_'))
    ['approve_kuh', 'approve_kumc', 'approve_kupi']
    >>> sorted(noticelog.DecisionRecords.institutions)
    ['kuh', 'kumc']

    >>> sorted(ddict.radio('what_for'))
    ... # doctest: +ELLIPSIS +NORMALIZE_WHITESPACE
    [('1', 'HERON Sponsorship'), ('2', 'HERON Data Use'),
     ('3', 'ACT Sponsor...'), ('4', 'Green HERON ...')]

    .. todo:: check expiration date

    '''

    SPONSORSHIP = '1'
    ACT_SPONSORSHIP = '3'
    GREENHERON_USE = '4'
    DATA_USE = '2'
    oversight_request_purposes = (SPONSORSHIP, DATA_USE,
                                  ACT_SPONSORSHIP, GREENHERON_USE)

    @inject(mc=medcenter.MedCenter,
            pm=i2b2pm.I2B2PM,
            dr=noticelog.DecisionRecords,
            stats=I2B2AggregateUsage,
            saa_rc=(redcap_connect.SurveySetup,
                    SAA_CONFIG_SECTION),
            dua_rc=(redcap_connect.SurveySetup,
                    DUA_CONFIG_SECTION),
            oversight_rc=(redcap_connect.SurveySetup,
                          OVERSIGHT_CONFIG_SECTION),
            oc=OversightCommittee,
            dg=disclaimer.DisclaimerGuard,
            smaker=(orm.session.Session,
                    redcapdb.CONFIG_SECTION),
            timesrc=rtconfig.Clock)
    def __init__(self, mc, pm, dr, stats, saa_rc, dua_rc, oversight_rc, oc,
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
        self._dua_survey_id = dua_rc.survey_id
        self._dua_rc = dua_rc
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
            context.sign_saa = Affiliate(badge, self._query,
                                         saa_rc=self._saa_rc)
        elif p is PERM_SIGN_DUA:
            context.sign_dua = Affiliate(badge, self._query,
                                         dua_rc=self._dua_rc)
        elif p is PERM_OVERSIGHT_REQUEST:
            context.oversight_request = self._oversight_request(badge)
        elif p is PERM_DROC_AUDIT:
            audit, dr = self.__oc._droc_auditor(badge)
            context.droc_audit = audit
            context.decision_records = dr
        elif p is PERM_STATS_REPORTER:
            context.stats_reporter = self.__stats
            context.browser = self._mc._browser
        elif p is PERM_START_I2B2:
            st = self._status(badge)
            if not st.complete:
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

        # redcap_connect uses the '%s@%s' pattern when recording
        # signatures, but we have traditionally looked this up
        # by badge.mail. When those didn't agree, we updated
        # the database to match badge.mail. So now we need
        # to check both.
        cn_at_domain = '%s@%s' % (badge.cn, self._saa_rc.domain)
        # Cache args have to be hashable
        mailboxes = frozenset([m for m in [badge.mail, cn_at_domain] if m])

        system_access_sigs = [sig.completion_time
                              for sig in self._signatures(mailboxes)]

        try:
            droc_audit = self.__oc._droc_auditor(badge)
        except NotDROC:
            droc_audit = None

        # Grace period for training enforcement ends July 1, 2015.
        enforce_training = str(self._t.today()) >= '2015-07-01'

        complete = (
            (current_training or not enforce_training) and
            system_access_sigs and (
                badge.is_executive() if self._pm.identified_data
                else
                (badge.is_faculty() or badge.is_executive() or sponsored)))

        return Status(faculty=badge.is_faculty(),
                      executive=badge.is_executive(),
                      sponsored=sponsored,
                      droc=droc_audit,
                      current_training=current_training,
                      expired_training=expired_training,
                      system_access_signed=system_access_sigs,
                      complete=bool(complete))

    def _sponsorship(self, uid,
                     ttl=timedelta(seconds=600)):
        not_sponsored = timedelta(seconds=1), None

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
            return not_sponsored

        return (
            # Noone is sponsored for identified data
            not_sponsored if self._pm.identified_data
            else
            self._query(('sponsorship', uid), do_q, 'Sponsorship'))

    def _training_current(self, badge):
        try:
            info = self._mc.latest_training(badge)
        except (IOError):
            log.warn('failed to look up training due to IOError')
            log.debug('training error detail', exc_info=True)
            return None, None
        except LookupError:
            log.info('no training on file for: %s (%s)',
                     badge.cn, badge.full_name())
            return None, None

        # convert dates to strings if the database hasn't already
        current = str(info.expired) >= str(self._t.today())
        if not current:
            log.info('training expired %s for: %s (%s)',
                     info.expired, badge.cn, badge.full_name())

        return (info, None) if current else (None, info)

    def _signatures(self, mailboxes,
                    ttl=timedelta(seconds=15)):
        '''Look up SAA survey response by email address(es).
        '''

        def mkq(mail):
            def q():
                return ttl, self._saa_rc.responses(mail)
            return q

        return [row
                for mail in mailboxes
                for row in
                self._query(('SAA', mail), mkq(mail), 'system access')]

    def _oversight_request(self, badge):
        log.debug('oversight_request: %s faculty? %s executive? %s',
                  badge, badge.is_faculty(), badge.is_executive())

        return OversightRequest(badge, self._mc._browser,
                                self._oversight_rc)

    def _redcap_rights(self, uid):
        r = redcapdb.redcap_user_rights
        return [row.project_id for row in self._smaker().
                execute(r.select(r.c.project_id).
                        where(r.c.username == uid))]


class NoPermission(TypeError):
    def __init__(self, whynot):
        self.whynot = whynot

    def __str__(self):
        return '%s(%s)' % (self.__class__.__name__, self.whynot)


class NotDROC(TypeError):
    pass


class Affiliate(Token):
    def __init__(self, badge, query, saa_rc=None, dua_rc=None):
        self.badge = badge
        self.__saa_rc = saa_rc
        self.__dua_rc = dua_rc
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

    def ensure_dua_survey(self, ttl=timedelta(seconds=15)):
        # TODO: redcap_connect should use notarized badges rather
        # than raw cn (copied from ensure_saa_survey())
        badge = self.badge

        def _ensure():
            fields = dict(user_id=badge.cn,
                          full_name=badge.sort_name())
            return (ttl, self.__dua_rc(badge.cn, fields))

        return self.__query(('DUA', badge.cn), _ensure, 'DUA link')


class OversightRequest(Token):
    '''Power to file authenticated oversight requests.
    '''
    def __init__(self, badge, browser, orc):
        self.__badge = badge
        self.__orc = orc
        self.__browser = browser

    def __repr__(self):
        return '%s(from=%s)' % (self.__class__.__name__, self.__badge.cn)

    def ensure_oversight_survey(self, uids, fac_id, what_for):
        if what_for not in HeronRecords.oversight_request_purposes:
            raise TypeError(what_for)

        tp = team_params(self.__browser.lookup, uids)
        fac = self.__browser.lookup(fac_id)
        from_faculty = self.__badge.cn == fac_id
        return self.__orc(
            self.__badge.cn if from_faculty else None,
            dict(tp,
                 faculty_name='%s, %s' % (
                     fac.sn, fac.givenname),
                 faculty_email=fac.mail,
                 request_from_faculty='01'[from_faculty],
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
     ('team_email_1', 'john.smith@js.example'),
     ('name_etc_1', 'Smith, John\nChair of Neurology...'),
     ('user_id_2', 'bill.student'),
     ('team_email_2', 'bill.student@js.example'),
     ('name_etc_2', 'Student, Bill\nStudent\nUndergrad')]

    '''
    nested = [[('user_id_%d' % (i + 1), uid),
               ('team_email_%d' % (i + 1), a.mail),
               ('name_etc_%d' % (i + 1), '%s, %s\n%s\n%s' % (
                   a.sn, a.givenname, a.title or '', a.ou or ''))]
              for (i, uid, a) in
              [(i, uids[i], lookup(uids[i]))
               for i in range(0, len(uids))]]
    return itertools.chain.from_iterable(nested)


class Mock(injector.Module, rtconfig.MockMixin):
    def __init__(self):
        import redcap_invite

        injector.Module.__init__(self)
        self.io = redcap_invite.MockIO()

    @singleton
    @provides((redcap_connect.SurveySetup, SAA_CONFIG_SECTION))
    def _rc_saa(self):
        opts = redcap_connect._test_settings
        return redcap_connect.SurveySetup(opts, self.io.connect, self.io.rng,
                                          survey_id=opts.survey_id)

    @singleton
    @provides((redcap_connect.SurveySetup, DUA_CONFIG_SECTION))
    def _rc_dua(self):
        opts = redcap_connect._test_settings
        return redcap_connect.SurveySetup(opts, self.io.connect, self.io.rng,
                                          survey_id=opts.survey_id)

    @singleton
    @provides((redcap_connect.SurveySetup, OVERSIGHT_CONFIG_SECTION))
    def _rc_oversight(self):
        opts = redcap_connect._test_settings
        return redcap_connect.SurveySetup(opts, self.io.connect, self.io.rng,
                                          project_id=opts.project_id)

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
    def __init__(self, ini):
        rtconfig.IniModule.__init__(self, ini)

    @singleton
    @provides((redcap_connect.SurveySetup, SAA_CONFIG_SECTION))
    @inject(rng=redcap_connect.KRandom,
            engine=(Connectable, redcap_invite.CONFIG_SECTION))
    def _rc_saa(self, rng, engine):
        opts = self.get_options(redcap_connect.OPTIONS, SAA_CONFIG_SECTION)
        return redcap_connect.SurveySetup(opts, engine.connect, rng,
                                          survey_id=opts.survey_id)

    @singleton
    @provides((redcap_connect.SurveySetup, DUA_CONFIG_SECTION))
    @inject(rng=redcap_connect.KRandom,
            engine=(Connectable, redcap_invite.CONFIG_SECTION))
    def _rc_dua(self, rng, engine):
        opts = self.get_options(redcap_connect.OPTIONS, DUA_CONFIG_SECTION)
        return redcap_connect.SurveySetup(opts, engine.connect, rng,
                                          survey_id=opts.survey_id)

    @singleton
    @provides((redcap_connect.SurveySetup, OVERSIGHT_CONFIG_SECTION))
    @inject(rng=redcap_connect.KRandom,
            engine=(Connectable, redcap_invite.CONFIG_SECTION))
    def _rc_oversight(self, rng, engine):
        opts = self.get_options(redcap_connect.OPTIONS + ('project_id',),
                                OVERSIGHT_CONFIG_SECTION)
        return redcap_connect.SurveySetup(opts, engine.connect, rng,
                                          survey_id=opts.survey_id,
                                          project_id=opts.project_id)

    @provides(disclaimer.KBadgeInspector)
    @inject(mc=medcenter.MedCenter)
    def notary(self, mc):
        return mc.getInspector()

    @classmethod
    def mods(cls, ini, **kwargs):
        return (
            [im for mcls in
             [medcenter.RunTime,
              i2b2pm.RunTime,
              redcap_connect.RunTime,
              disclaimer.RunTime,
              noticelog.RunTime]
             for im in mcls.mods(ini=ini, **kwargs)] +
            [cls(ini)])

    @classmethod
    def _integration_test(cls, mc, hr, userid):  # pragma nocover
        req = medcenter.MockRequest()
        req.remote_user = userid
        mc.authenticated(userid, req)
        hr.grant(req.context, PERM_STATUS)
        print(req.context.status)

        hr.grant(req.context, PERM_START_I2B2)
        print(req.context.start_i2b2())


if __name__ == '__main__':  # pragma nocover
    def _script():
        from datetime import datetime
        from io import open as io_open
        from os import listdir
        from os.path import join as joinpath
        from random import Random
        from sys import argv, stderr, path as sys_path
        from urllib2 import build_opener
        import uuid

        from sqlalchemy import create_engine
        import ldap

        cwd = Path('.', open=io_open, joinpath=joinpath, listdir=listdir)
        logging.basicConfig(level=logging.DEBUG, stream=stderr)

        sys_path.append('..')
        import traincheck

        userid, config_fn = argv[1:3]
        ini = cwd / config_fn
        trainingfn = traincheck.from_config(ini, create_engine)

        mc, hr = RunTime.make([medcenter.MedCenter, HeronRecords],
                              ini=ini,
                              rng=Random(),
                              timesrc=datetime,
                              uuid=uuid,
                              urlopener=build_opener(),
                              trainingfn=trainingfn,
                              ldap=ldap,
                              create_engine=create_engine)
        RunTime._integration_test(mc, hr, userid)

    _script()
