'''heron_policy.py -- HERON policy decisions, records

  # logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)  #@@
  >>> mc, hp, dr, _ = Mock.make_stuff()
  >>> mcmock = medcenter.Mock

.. todo:: explain our use of injector a bit

Suppose an investigator and some students log in::

  >>> facreq = mcmock.login_info('john.smith')
  >>> mc.issue(facreq)
  [<MedCenter sealed box>]
  >>> stureq = mcmock.login_info('bill.student')
  >>> mc.issue(stureq)
  [<MedCenter sealed box>]
  >>> stu2req = mcmock.login_info('some.one')
  >>> mc.issue(stu2req)
  [<MedCenter sealed box>]

See if they're qualified faculty::

  >>> hp.issue(facreq)
  [Faculty(John Smith <john.smith@js.example>)]
  >>> facreq.faculty
  Faculty(John Smith <john.smith@js.example>)

  >>> facreq.user.ensure_saa_survey()
  'http://bmidev1/redcap-host/surveys/?s=8074&full_name=Smith%2C+John&user_id=john.smith'

  >>> hp.issue(stureq)
  [Affiliate(Bill Student <bill.student@js.example>)]
  >>> stureq.faculty is None
  True
  >>> facreq.faculty.ensure_oversight_survey(['some.one'],
  ...                                        what_for='2')
  'http://bmidev1/redcap-host/surveys/?s=8074&full_name=Smith%2C+John&multi=yes&name_etc_1=One%2C+Some%0A%0A&user_id=john.smith&user_id_1=some.one&what_for=2'

See if the students are qualified in some way::

  >>> stureq.user.repository_account()
  Traceback (most recent call last):
    ...
  NotSponsored

  >>> stureq.user.training()
  Traceback (most recent call last):
  ...
  NoTraining

  >>> hp.issue(stu2req)
  [Affiliate(Some One <some.one@js.example>)]

.. todo:: secure represention of sponsor rather than True/False?
  >>> stu2req.user.sponsor()
  True

  >>> stu2req.user.training()
  '2012-01-01'
  >>> stu2req.user.repository_account()
  Traceback (most recent call last):
  ...
  NoAgreement


Get an actual access qualification; i.e. check for
system access agreement and human subjects training::

  >>> facreq.user.repository_account()
  Access(Faculty(John Smith <john.smith@js.example>))

Executives don't need sponsorship::
  >>> exreq = mcmock.login_info('big.wig')
  >>> mc.issue(exreq)
  [<MedCenter sealed box>]
  >>> hp.issue(exreq)
  [Executive(Big Wig <big.wig@js.example>)]
  >>> exreq.user.repository_account()
  Access(Executive(Big Wig <big.wig@js.example>))


Directory Search
----------------

  >>> facreq.user.browser.lookup('some.one')
  Some One <some.one@js.example>
  >>> facreq.user.browser.search(5, 'john.smith', '', '')
  [John Smith <john.smith@js.example>]

Recovery from Database Errors
-----------------------------

We count on sqlalchemy to do this.


Oversight Decisions
-------------------

Which users should we notify?

  >>> ds = dr.oversight_decisions()
  >>> ds
  [(34, u'-8650809471427594162', u'1', 3)]

Get details that we might want to use in composing the notification::
  >>> from pprint import pprint
  >>> for pid, record, decision, qty in ds:
  ...    pprint(dr.decision_detail(record))
  (John Smith <john.smith@js.example>,
   [Some One <some.one@js.example>, Carol Student <carol.student@js.example>],
   {u'approve_kuh': u'1',
    u'approve_kumc': u'1',
    u'approve_kupi': u'1',
    u'full_name': u'John Smith',
    u'project_title': u'Cure Warts',
    u'user_id': u'john.smith',
    u'user_id_1': u'some.one',
    u'user_id_2': u'carol.student'})

'''

import datetime
import itertools
import logging
import urllib

import injector
from injector import inject, provides, singleton
import sqlalchemy
from sqlalchemy.sql import select, and_, func

import config
import i2b2pm
import medcenter
import redcap_connect
import sealing
import redcapdb
import noticelog
import disclaimer
from disclaimer import Disclaimer, Acknowledgement, KTimeSource

SAA_CONFIG_SECTION='saa_survey'
OVERSIGHT_CONFIG_SECTION='oversight_survey'
PERM_USER=__name__ + '.user'
PERM_FACULTY=__name__ + '.faculty'

log = logging.getLogger(__name__)


class HeronRecords(object):
    permissions = (PERM_USER, PERM_FACULTY)
    institutions = ('kuh', 'kupi', 'kumc')

    @inject(mc=medcenter.MedCenter,
            pm=i2b2pm.I2B2PM,
            saa_opts=(config.Options, SAA_CONFIG_SECTION),
            oversight_opts=(config.Options, OVERSIGHT_CONFIG_SECTION),
            engine=(sqlalchemy.engine.base.Connectable, redcapdb.CONFIG_SECTION),
            smaker=(sqlalchemy.orm.session.Session, redcapdb.CONFIG_SECTION),
            timesrc=KTimeSource,
            urlopener=urllib.URLopener)
    def __init__(self, mc, pm, saa_opts, oversight_opts,
                 engine, smaker, timesrc, urlopener):
        log.debug('HeronRecords.__init__ again?')
        self._engine = engine
        self._smaker = smaker
        self._mc = mc
        self._pm = pm
        self._t = timesrc
        self._saa_survey_id = saa_opts.survey_id
        ## refactor so these two are passed in rather than opts/urlopener?
        self._saa_rc = redcap_connect.survey_setup(saa_opts, urlopener)
        self._oversight_rc = redcap_connect.survey_setup(oversight_opts,
                                                         urlopener)
        self._oversight_project_id = oversight_opts.project_id
        self._executives = oversight_opts.executives.split()

    def issue(self, req):
        mc = self._mc

        hr = self
        badge = req.badge

        # limit capabilities of self to one user
        class I2B2Account(object):
            def __init__(self, agent):
                self.agent = agent

            def login(self):
                hr._pm.ensure_account(badge.cn)

            def __repr__(self):
                return 'Access(%s)' % self.agent

        class Browser(object):
            ''''Users get to do LDAP searches,
            but they don't get to exercise the rights of
            the users they find.
            '''
            def lookup(self, uid):
                return mc.lookup(uid)
            def search(self, max, cn, sn, givenname):
                return mc.search(max, cn, sn, givenname)

        class Record(object):
            def ensure_saa(self, params):
                return hr._saa_rc(badge.cn, params)

            def get_sig(self):
                return hr._check_saa_signed(badge.mail)  #@@seal date

            def ensure_oversight(self, params):
                return hr._oversight_rc(badge.cn, params, multi=True)

            def get_training(self):
                try:
                    when = mc.training(req.idvault_entry)
                except (KeyError):
                    raise NoTraining
                except (IOError):
                    log.warn('failed to look up training due to IOError')
                    log.debug('training error detail', exc_info=True)
                    raise NoTraining
                current = when >= hr._t.today().isoformat()
                if not current:
                    raise NoTraining(when)
                return when

            def get_sponsor(self):
                return hr._sponsored(badge.cn)  #@@ seal sponsor uid

            def repository_account(self, user, sponsor, sig, training):
                #@@ todo: check user, sponsor, sig, training?
                return I2B2Account(user)

        ex = fac = user = None
        req.disclaimer, ack = self._disclaimer_acknowledgement(badge.cn)
        log.debug('disclaimer: %s', req.disclaimer)
        log.debug('ack: %s', ack)
        if badge.cn in self._executives:
            ex = Executive(badge,
                           req.idvault_entry,
                           Record(), Browser(), ack)
            user = ex
        else:
            try:
                fac = Faculty(mc.faculty_badge(req.idvault_entry),
                               req.idvault_entry,
                               Record(), Browser(), ack)
                user = fac
            except medcenter.NotFaculty:
                user = Affiliate(badge, req.idvault_entry, Record(), Browser(), ack)

        req.executive = ex
        req.faculty = fac
        req.user = user

        return [user]

    def audit(self, cap, p=PERM_USER):
        log.info('HeronRecords.audit(%s, %s)' % (cap, p))
        if not isinstance(cap, Faculty if p is PERM_FACULTY else Affiliate):
            raise TypeError
        self._mc.read_badge(cap.idcap)

    def _disclaimer_acknowledgement(self, user_id):
        '''
        @returns: (current disclaimer, acknowledgement of user_id); ack is None if not found.
        '''
        s = self._smaker()

        d = s.query(Disclaimer).filter(Disclaimer.current==1).first()

        if d:
            log.debug('current disclaimer address: %s', d.url)
            a = s.query(Acknowledgement \
                            ).filter(Acknowledgement.disclaimer_address==d.url
                                     ).filter(Acknowledgement.user_id==user_id).first()
        else:
            log.warn('no current disclaimer!')
            log.debug('session engine: %s', s.bind)
            a = None

        return d, a

    def _check_saa_signed(self, mail):
        '''Test for an authenticated SAA survey response.
        '''
        if not self._engine.execute(_saa_query(mail, self._saa_survey_id)).fetchall():
            raise NoAgreement()

    def q_executive(self, agent):
        raise NotExecutive()
        # TODO: port this to mysql/redcap
        if not self._agent_test('''select 1
                         from heron.exec_group where user_id=:u
		         and status ='A' ''', 'u', agent):
            raise NotExecutive()
        return OK(agent)

    def _sponsored(self, uid):
        '''Test for sponsorship approval from each participating institution.

        In the oversight_project, we assume userid of sponsored users
        are stored in REDCap fields with names like user_id_% and
        approval decisions are stored in fields with names like
        approve_%, with a distinct approve_% field for each
        participating institution and coded yes=1/no=2/defer=3.

        .. todo:: check expiration date
        '''

        decision, candidate, dc = _sponsor_queries(self._oversight_project_id)

        q = dc.select(dc.c.candidate==uid)

        if not self._engine.execute(q).fetchall():
            raise NotSponsored()

        return True


class DecisionRecords(object):
    @inject(rt=(config.Options, OVERSIGHT_CONFIG_SECTION),
            engine=(sqlalchemy.engine.base.Connectable,
                    redcapdb.CONFIG_SECTION),
            smaker=(sqlalchemy.orm.session.Session, redcapdb.CONFIG_SECTION),
            mc=medcenter.MedCenter)
    def __init__(self, rt, engine, mc, smaker):
        self._oversight_project_id = rt.project_id
        self._engine = engine
        self._mc = mc
        #smaker is just to pull in dependencies. hm.

    def oversight_decisions(self):
        '''In order to facilitate email notification of committee
        decisions, find decisions where notification has not been sent.
        '''
        cd, who, cdwho = _sponsor_queries(self._oversight_project_id)

        # decisions without notifications
        nl = noticelog.notice_log
        dwn = cd.outerjoin(nl).select() \
            .with_only_columns(cd.columns).where(nl.c.record == None)
        return self._engine.execute(dwn).fetchall()

    def decision_detail(self, record):
        avl = list(redcapdb.allfields(self._engine,
                                      self._oversight_project_id,
                                      record))
        mc = self._mc
        team = [mc.lookup(user_id)
                for user_id in
                [v for a, v in avl if v and a.startswith('user_id_')]]

        d = dict(avl)
        investigator = mc.lookup(d['user_id'])
        return investigator, team, d


def _saa_query(mail, survey_id):
    '''
      >>> q = _saa_query('john.smith@js.example', 11)
      >>> print str(q)
      SELECT r.response_id, r.participant_id, r.record, r.first_submit_time, r.completion_time, r.return_code, p.participant_id, p.survey_id, p.arm_id, p.hash, p.legacy_hash, p.participant_email, p.participant_identifier 
      FROM redcap_surveys_response AS r JOIN redcap_surveys_participants AS p ON r.participant_id = p.participant_id 
      WHERE p.participant_email = :participant_email_1 AND p.survey_id = :survey_id_1

    '''
    r = redcapdb.redcap_surveys_response.alias('r')
    p = redcapdb.redcap_surveys_participants.alias('p')
    return r.join(p, r.c.participant_id == p.c.participant_id).select().where(
            and_(p.c.participant_email==mail, p.c.survey_id==survey_id))


def _sponsor_queries(oversight_project_id):
    '''
      >>> from pprint import pprint
      >>> decision, candidate, cdwho = _sponsor_queries(123)

      >>> print str(decision)
      SELECT redcap_data.project_id, redcap_data.record, redcap_data.value AS decision, count(*) AS count_1 
      FROM redcap_data 
      WHERE redcap_data.field_name LIKE :field_name_1 AND redcap_data.project_id = :project_id_1 GROUP BY redcap_data.project_id, redcap_data.record, redcap_data.value 
      HAVING count(*) = :count_2

      >>> pprint(decision.compile().params)
      {u'count_2': 3, u'field_name_1': 'approve_%', u'project_id_1': 123}


      >>> print str(candidate) # doctest: +NORMALIZE_WHITESPACE
      SELECT redcap_data.project_id, redcap_data.record, redcap_data.value AS userid 
      FROM redcap_data 
      WHERE redcap_data.field_name LIKE :field_name_1

      >>> pprint(candidate.compile().params)
      {u'field_name_1': 'user_id_%'}

      >>> print str(cdwho) # doctest: +NORMALIZE_WHITESPACE
      SELECT cd_record AS record,
             cd_decision AS decision,
             who_userid AS candidate 
      FROM
        (SELECT cd.project_id AS cd_project_id,
                cd.record AS cd_record,
                cd.decision AS cd_decision,
                cd.count_1 AS cd_count_1,
                who.project_id AS who_project_id,
                who.record AS who_record,
                who.userid AS who_userid 
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
           AND who.project_id = cd.project_id) AS cdwho

      >>> pprint(cdwho.compile().params)
      {u'count_2': 3,
       u'field_name_1': 'approve_%',
       u'field_name_2': 'user_id_%',
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
             rd.c.project_id==oversight_project_id)
        ).group_by(rd.c.project_id,
                   rd.c.record,
                   rd.c.value).having(
            func.count() == len(HeronRecords.institutions)).alias('cd')

    # todo: consider combining record, event, project_id into one attr
    candidate = select((rd.c.project_id, rd.c.record,
                        rd.c.value.label('userid'))).where(
        and_(rd.c.field_name.like('user_id_%'))).alias('who')

    j = decision.join(candidate,
                      and_(candidate.c.record == decision.c.record,
                           candidate.c.project_id == decision.c.project_id)
                      ).alias('cdwho').select()
        
    cdwho = j.with_only_columns((j.c.cd_record.label('record'),
                                 j.c.cd_decision.label('decision'),
                                 j.c.who_userid.label('candidate')))

    return decision, candidate, cdwho


class NoPermission(Exception):
    pass


class NotSponsored(NoPermission):
    pass


class NoTraining(NoPermission):
    def __init__(self, when=None):
        self.when = when


class NotExecutive(NoPermission):
    pass


class NoAgreement(NoPermission):
    pass



class Affiliate(object):
    def __init__(self, badge, idcap, record, browser, ack):
        self.badge = badge
        self.idcap = idcap
        self.record = record
        self.browser = browser
        self.acknowledgement = ack

    def __repr__(self):
        return 'Affiliate(%s)' % (self.badge)

    def sort_name(self):
        # law of demeter says move this to Badge()...
        return "%s, %s" % (self.badge.sn, self.badge.givenname)
        
    def ensure_saa_survey(self):
        return self.record.ensure_saa(dict(user_id=self.badge.cn,
                                           full_name=self.sort_name()))

    def signature(self):
        return self.record.get_sig()

    def training(self):
        return self.record.get_training()

    def sponsor(self):
        return self.record.get_sponsor()

    def repository_account(self):
        return self.record.repository_account(self,
                                              self.sponsor(),
                                              self.signature(),
                                              self.training())

class Executive(Affiliate):
    def __repr__(self):
        return 'Executive(%s)' % (self.badge)

    def sponsor(self):
        return self

    
class Faculty(Affiliate):
    oversight_request_purposes = ('1',  # sponsorship
                                  '2')  # data use
    def __repr__(self):
        return 'Faculty(%s)' % (self.badge)

    def sponsor(self):
        return self

    def ensure_oversight_survey(self, uids, what_for):
        if what_for not in self.oversight_request_purposes:
            raise TypeError

        tp = team_params(self.browser.lookup, uids)
        return self.record.ensure_oversight(dict(tp,
                                                 user_id=self.badge.cn,
                                                 full_name=self.sort_name(),
                                                 what_for=what_for,
                                                 multi='yes'))

def team_params(lookup, uids):
    r'''
    >>> import pprint
    >>> pprint.pprint(list(team_params(medcenter.Mock.make().lookup,
    ...                                ['john.smith', 'bill.student'])))
    [('user_id_1', 'john.smith'),
     ('name_etc_1', 'Smith, John\nChair of Department of Neurology\n'),
     ('user_id_2', 'bill.student'),
     ('name_etc_2', 'Student, Bill\n\n')]

    '''
    nested = [[('user_id_%d' % (i+1), uid),
               ('name_etc_%d' % (i+1), '%s, %s\n%s\n%s' % (
                    a.sn, a.givenname, a.title, a.ou))]
              for (i, uid, a) in 
              [(i, uids[i], lookup(uids[i]))
               for i in range(0, len(uids))]]
    return itertools.chain.from_iterable(nested)



class TestSetUp(disclaimer.TestSetUp):
    @singleton
    @provides((sqlalchemy.orm.session.Session, redcapdb.CONFIG_SECTION))
    @inject(engine=(sqlalchemy.engine.base.Connectable, redcapdb.CONFIG_SECTION),
            timesrc=KTimeSource,
            srt=(config.Options, SAA_CONFIG_SECTION),
            ort=(config.Options, OVERSIGHT_CONFIG_SECTION))
    def redcap_sessionmaker(self, engine, timesrc, srt, ort):
        smaker = super(TestSetUp, self).redcap_sessionmaker(engine=engine)
        s = smaker()
        def insert_eav(e, n, v):
            s.execute(redcapdb.redcap_data.insert().values(
                    project_id=ort.project_id,
                    record=e, event_id=1, field_name=n, value=v))

        # approve 2 users in 1 request
        e = hash('john.smith')
        for a, v in {'user_id': 'john.smith',
                     'full_name': 'John Smith',
                     'project_title': 'Cure Warts'}.iteritems():
            insert_eav(e, a, v)
        for n, userid in ((1, 'some.one'), (2, 'carol.student')):
            insert_eav(e, 'user_id_%d' % n, userid)
        for org in HeronRecords.institutions:
            for a, v in {'approve_%s' % org: 1}.iteritems():
                insert_eav(e, a, v)

        # some rejections for bill.student:
        for userid in ['bill.student']:
            for n, v in {'user_id_1': userid,
                         'user_id': 'john.smith',
                         'full_name': 'John Smith'}.iteritems():
                insert_eav(hash(userid), n, v)
            for org in HeronRecords.institutions[:2]:
                for n, v in {'approve_' + org: 2}.iteritems():
                    insert_eav(hash(userid), n, v)

        log.debug('add SAA records')
        redcapdb.redcap_surveys_participants.create(s.bind)
        s.commit()
        redcapdb.redcap_surveys_response.create(s.bind)
        noticelog.notice_log.schema = None  # sqlite doesn't grok schemas
        noticelog.notice_log.create(s.bind)
        for email in ['john.smith@js.example', 'big.wig@js.example']:
            s.execute(redcapdb.redcap_surveys_participants.insert().values(
                    participant_id=abs(hash(email)),
                    survey_id=srt.survey_id, participant_email=email))
            s.execute(redcapdb.redcap_surveys_response.insert().values(
                    response_id=abs(hash(email)), record=abs(hash(email)),
                    completion_time=timesrc.today() + datetime.timedelta(days=-7),
                    participant_id=abs(hash(email))))

        s.commit()
        return smaker

class Mock(injector.Module):

    @provides((config.Options, SAA_CONFIG_SECTION))
    def saa_settions(self):
        return redcap_connect._test_settings

    @provides((config.Options, OVERSIGHT_CONFIG_SECTION))
    def oversight_settings(self):
        return redcap_connect._test_settings

    @provides(urllib.URLopener)
    def redcap_connect_web_ua(self):
        return redcap_connect._TestUrlOpener()

    @classmethod
    def mods(cls):
        log.debug('heron_policy.Mock.mods')
        return medcenter.Mock.mods() + i2b2pm.Mock.mods() + disclaimer.Mock.mods() + [
            TestSetUp(), Mock()]

    @classmethod
    def depgraph(cls):
        return injector.Injector(cls.mods())

    @classmethod
    def make_stuff(cls, mods=None, what=(medcenter.MedCenter,
                                         HeronRecords, DecisionRecords, None)):
        if not mods:
            mods = cls.mods()
        depgraph = injector.Injector(mods)
        return [depgraph.get(kls) if kls else depgraph
                for kls in what]

    @classmethod
    def login_sim(cls, mc, hr):
        def mkrole(uid):
            req = medcenter.Mock.login_info(uid)
            caps = mc.issue(req) + hr.issue(req)
            return req.user, req.faculty, req.executive
        return mkrole


class RunTime(injector.Module):  # pragma nocover
    def __init__(self, ini):
        injector.Module.__init__(self)
        self._ini = ini

    def configure(self, binder):
        import datetime
        import urllib2
        binder.bind(KTimeSource,
                    injector.InstanceProvider(datetime.datetime))

        def bind_options(names, section):
            rt = config.RuntimeOptions(names)
            rt.load(self._ini, section)
            binder.bind((config.Options, section), rt)

        bind_options(['survey_id'], SAA_CONFIG_SECTION)
        bind_options(['project_id', 'executives'], OVERSIGHT_CONFIG_SECTION)

        binder.bind(urllib.URLopener, urllib2.build_opener)

    @classmethod
    def mods(cls, ini='integration-test.ini'):
        return (medcenter.RunTime.mods(ini) +
                i2b2pm.RunTime.mods(ini) +
                redcapdb.RunTime.mods(ini) +
                disclaimer.RunTime.mods(ini) +
                [cls(ini)])

    @classmethod
    def depgraph(cls):
        return injector.Injector(cls.mods())


if __name__ == '__main__':  # pragma nocover
    import sys

    logging.basicConfig(level=logging.DEBUG, stream=sys.stderr)

    userid = sys.argv[1]
    depgraph = RunTime.depgraph()
    req = medcenter.Mock.login_info(userid)
    hr = depgraph.get(HeronRecords)
    hr._mc.issue(req) # umm... peeking
    hr.issue(req)
    print req.user.repository_account()

    ds = depgraph.get(DecisionRecords)
    print "pending notifications:", ds.oversight_decisions()
