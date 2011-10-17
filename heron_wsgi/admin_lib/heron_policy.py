'''heron_policy.py -- HERON policy decisions, records

  # logging.basicConfig(level=logging.DEBUG)
  >>> mc, hp, _ = Mock.make_stuff()
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

  >>> _TestEngine().connect(reset=True) and None
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
  >>> facreq.faculty.ensure_oversight_survey(dict(title='cure everything'),
  ...                                        what_for='2')
  'http://bmidev1/redcap-host/surveys/?s=8074&full_name=Smith%2C+John&multi=yes&title=cure+everything&user_id=john.smith&what_for=2'

See if the students are qualified in some way::

  >>> _TestEngine().connect(reset=True) and None
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

  >>> _TestEngine().connect(reset=True) and None
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

Make sure we recover, eventually, after database errors::

    >>> [facreq.user.signature() for i in range(1, 10)]
    Traceback (most recent call last):
      ...
    IOError: databases fail sometimes; deal

    >>> facreq.user.repository_account()
    Access(Faculty(John Smith <john.smith@js.example>))

'''

import urllib
import logging

import injector
from injector import inject, provides
import sqlalchemy

import config
import i2b2pm
import medcenter
import redcap_connect
import sealing
import redcapdb
import disclaimer
from disclaimer import Disclaimer, Acknowledgement

SAA_CONFIG_SECTION='saa_survey'
OVERSIGHT_CONFIG_SECTION='oversight_survey'
PERM_USER=__name__ + '.user'
PERM_FACULTY=__name__ + '.faculty'

KTimeSource = injector.Key('TimeSource')

log = logging.getLogger(__name__)

class HeronRecords(object):
    permissions = (PERM_USER, PERM_FACULTY)
    qty_institutions = len(('kuh', 'kupi', 'kumc'))

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
                return mc._lookup(uid)  #@@ peeking
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
                except (KeyError, IOError):
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

        log.debug('current disclaimer address: %s', d.url)
        a = s.query(Acknowledgement \
                        ).filter(Acknowledgement.disclaimer_address==d.url
                                 ).filter(Acknowledgement.user_id==user_id).first()
        return d, a

    def _check_saa_signed(self, mail):
        '''Test for an authenticated SAA survey response.
        '''
        ans = self._engine.execute(
            '''select p.survey_id, p.participant_email, r.response_id, r.record, r.completion_time
               from redcap_surveys_response r
                 join redcap_surveys_participants p on p.participant_id = r.participant_id 
               where p.participant_email=%(mail)s and p.survey_id = %(survey_id)s''',
            {'mail': mail, 'survey_id': self._saa_survey_id})

        if not ans.fetchmany():
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
        ans = self._engine.execute('''
select record, count(*)
from (
select distinct
  candidate.record, candidate.userid, review.institution, review.decision
from (
  select record, value as userid
  from redcap_data
  where project_id=%(project_id)s
  and field_name like 'user_id_%%'
) as candidate
join  (
  select record, field_name as institution, value as decision
  from redcap_data
  where project_id=%(project_id)s
  and field_name like 'approve_%%'
) as review on review.record = candidate.record
where decision=1 and userid=%(userid)s
) review
having count(*) = %(qty)s
'''
                                    , dict(project_id=self._oversight_project_id,
                                           userid=uid,
                                           qty=self.qty_institutions))

        if not ans.fetchall():
            raise NotSponsored()
        return True


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

    def ensure_oversight_survey(self, team_params, what_for):
        if what_for not in self.oversight_request_purposes:
            raise TypeError
        return self.record.ensure_oversight(dict(team_params,
                                                 user_id=self.badge.cn,
                                                 full_name=self.sort_name(),
                                                 what_for=what_for,
                                                 multi='yes'))


class Mock(injector.Module):
    def configure(self, binder):
        binder.bind(KTimeSource, _TestTimeSource),
        binder.bind((config.Options, SAA_CONFIG_SECTION),
                    redcap_connect._test_settings)
        binder.bind((config.Options, OVERSIGHT_CONFIG_SECTION),
                    redcap_connect._test_settings)

        binder.bind(urllib.URLopener, redcap_connect._TestUrlOpener)

    @provides((sqlalchemy.engine.base.Connectable, redcapdb.CONFIG_SECTION))
    def mock_engine(self):
        return _TestEngine()

    @classmethod
    def mods(cls):
        return medcenter.Mock.mods() + i2b2pm.Mock.mods() + [Mock()]

    @classmethod
    def depgraph(cls):
        return injector.Injector(cls.mods())

    @classmethod
    def make_stuff(cls, mods=None):
        if not mods:
            mods = cls.mods()
        depgraph = injector.Injector(mods)
        mc = depgraph.get(medcenter.MedCenter)
        hr = depgraph.get(HeronRecords)
        return mc, hr, depgraph

    @classmethod
    def login_sim(cls, mc, hr):
        def mkrole(uid):
            req = medcenter.Mock.login_info(uid)
            caps = mc.issue(req) + hr.issue(req)
            return req.user, req.faculty, req.executive
        return mkrole


class _TestTimeSource(object):
    def today(self):
        import datetime
        return datetime.date(2011, 9, 2)


_d = None
class _TestEngine(object):

    def connect(self, reset=False):
        global _d

        if reset or _d is None or _d.hosed:
            _d = _TestDBConn()

        return _d

    def execute(self, q, params=[]):
        return self.connect().execute(q, params)


class _TestDBConn(object):
    signed_users=['john.smith@js.example',
                  'big.wig@js.example']
    def __init__(self):
        self._ticks = 0
        self.hosed = False

    def execute(self, q, params=[]):
        self._ticks += 1
        if self._ticks % 7 == 0:
            self.hosed = True

        if self.hosed:
            raise IOError, 'databases fail sometimes; deal'

        if ('mail' in params and 'survey_id' in params
            and params['mail'] in self.signed_users):
            results = [(params['survey_id'],
                        params['mail'], 123, 123, '2011-01-01')]
        elif 'count' in q:  # assume it's the sponsored query
            if 'some.one' in params.get('userid', ''):
                results = [(9, 3)]
            else:
                results = []
        else:
            results = []

        return _TestResults(results)


class _TestResults():
    def __init__(self, results):
        self._results = results
        self._row = 0

    def fetchmany(self):
        return self._results

    def fetchall(self):
        return self._results

    def fetchone(self):
        row = self._results[self._row]
        self._row += 1
        return row


class RunTime(injector.Module):  # pragma nocover
    def __init__(self, ini):
        injector.Module.__init__(self)
        self._ini = ini

    def configure(self, binder):
        import datetime
        import urllib2
        binder.bind(KTimeSource,
                    injector.InstanceProvider(datetime.date))

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

    userid = sys.argv[1]
    depgraph = RunTime.depgraph()
    req = medcenter.Mock.login_info(userid)
    hr = depgraph.get(HeronRecords)
    hr._mc.issue(req) # umm... peeking
    hr.issue(req)
    print req.user.repository_account()
