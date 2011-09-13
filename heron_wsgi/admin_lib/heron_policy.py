'''heron_policy.py -- HERON policy decisions, records

  >>> m = medcenter._mock()
  >>> hp = HeronRecords(_TestDBConn(), m, _TestTimeSource(),
  ...                   saa_survey_id=11, oversight_project_id=34, qty_institutions=3)


Look up an investigator and a student::
  >>> fac = m.affiliate('john.smith')
  >>> fac
  John Smith <john.smith@js.example>
  >>> stu = m.affiliate('bill.student')
  >>> stu2 = m.affiliate('some.one')

See if they're qualified faculty::
  >>> hp.q_faculty(fac)
  OK:John Smith <john.smith@js.example>
  >>> hp.q_faculty(stu)
  Traceback (most recent call last):
    ...
  NotFaculty

See if the students are qualified in some way::

  >>> hp.q_any(stu)
  Traceback (most recent call last):
    ...
  NotSponsored

  >>> hp.q_any(stu2)
  OK:Some One <some.one@js.example>

Get an actual access qualification; i.e. check for
system access agreement and human subjects training::
  >>> hp.repositoryAccess(hp.q_any(fac))
  Access(John Smith <john.smith@js.example>)

'''

from db_util import transaction, oracle_connect, mysql_connect
import config

import medcenter

REDCAPDB_CONFIG_SECTION='redcapdb'


class HeronRecords(object):
    # TODO: connection pooling/management?
    def __init__(self, conn, medcenter, timesrc,
                 saa_survey_id, oversight_project_id, qty_institutions):
        self._conn = conn
        self._m = medcenter
        self._t = timesrc
        self._saa_survey_id = saa_survey_id
        self._oversight_project_id = oversight_project_id
        self.qty_institutions = qty_institutions

    def check_saa_signed(self, agent):
        '''Test for an authenticated SAA survey response bearing the agent's email address.
        '''
        with transaction(self._conn) as q:
            q.execute(
                '''select p.survey_id, p.participant_email, r.response_id, r.record, r.completion_time
 		   from redcap_surveys_response r
                     join redcap_surveys_participants p on p.participant_id = r.participant_id 
		   where p.participant_email=%(mail)s and p.survey_id = %(survey_id)s''',
                {'mail': agent.mail, 'survey_id': self._saa_survey_id})
            ok = len(q.fetchmany()) > 0
        if not ok:
            raise NoAgreement()

    def q_executive(self, agent):
        raise NotExecutive()
        # TODO: port this to mysql/redcap
        if not self._agent_test('''select 1
                         from heron.exec_group where user_id=:u
		         and status ='A' ''', 'u', agent):
            raise NotExecutive()
        return OK(agent)

    def q_faculty(self, agent):
        '''Test whether the medcenter considers this agent to be faculty.
        '''
        self._m.checkFaculty(agent)
        return OK(agent)

    def q_sponsored(self, agent):
        '''Test for sponsorship approval from each participating institution.

        In the oversight_project, we assume userid of sponsored users
        are stored in REDCap fields with names like user_id_% and
        approval decisions are stored in fields with names like
        approve_%, with a distinct approve_% field for each
        participating institution and coded yes=1/no=2/defer=3.
        '''
        with transaction(self._conn) as q:
            q.execute('''
select record, count(*)
from (
select distinct
  candidate.record, candidate.userid, review.institution, review.decision
from (
  select record, value as userid
  from redcap_data
  where project_id=:project_id
  and field_name like 'user_id_%'
) as candidate
join  (
  select record, field_name as institution, value as decision
  from redcap_data
  where project_id=:project_id
  and field_name like 'approve_%'
) as review on review.record = candidate.record
where decision=1 and userid=:userid
) review
having count(*) = :qty
'''
                      , dict(project_id=self._oversight_project_id,
                             userid=agent.userid(),
                             qty=self.qty_institutions))
            answers = q.fetchall()

        if not answers:
            raise NotSponsored()
        return OK(agent)

    def q_any(self, agent):
        try:
            return self.q_faculty(agent)
        except medcenter.NotFaculty:
            try:
                return self.q_executive(agent)
            except NoPermission:
                return self.q_sponsored(agent)

    def _agent_test(self, sql, k, agent):
        with transaction(self._conn) as q:
            q.execute(sql, {k: agent.userid()})
            return len(q.fetchall()) > 0

    def repositoryAccess(self, q):
        a = q.agent
        try:
            texp = self._m.trainedThru(a)
        except KeyError:
            raise NoTraining("no training on file")
        if texp < self._t.today().isoformat():
            raise NoTraining("training out of date")
        self.check_saa_signed(a)
        return Access(a, texp, Disclaimer(a))


class NoPermission(Exception):
    pass
class NotSponsored(NoPermission):
    pass
class NoTraining(NoPermission):
    pass
class NotExecutive(NoPermission):
    pass
class NoAgreement(NoPermission):
    pass


class OK(object):
    def __init__(self, agent):
        self.agent = agent
    def __repr__(self):
        return 'OK:' + repr(self.agent)

class Access(object):
    def __init__(self, agent, texp, discl):
        self._agent = agent

    def __str__(self):
        return 'Access(%s)' % self._agent
    def __repr__(self):
        return str(self)


class Disclaimer(object):
    '''
    .. todo: route users thru disclaimer
    '''
    def __init__(self, agent):
        self._agent = agent


def setup_connection(ini, section=REDCAPDB_CONFIG_SECTION):
    '''
    .. todo: refactor into datasource
    '''
    rt = config.RuntimeOptions('user password host sid engine'.split())
    rt.load(ini, section)
    #return oracle_connect(rt.user, rt.password, rt.host, 1521, rt.sid)
    return mysql_connect(rt.user, rt.password, rt.host, 3306, 'redcap')


def _mock(ini='integration-test.ini'):
    m = medcenter._mock()

    survey_id = 11  # arbitrary
    return HeronRecords(_TestDBConn(), m, _TestTimeSource(), survey_id)


class _TestTimeSource(object):
    def today(self):
        import datetime
        return datetime.date(2011, 9, 2)


class _TestDBConn(object):
    def cursor(self):
        return _TestTrx()

    def commit(self):
        pass

class _TestTrx():
    def __init__(self):
        self._results = None

    def execute(self, q, params=[]):
        if params == {'mail': 'john.smith@js.example', 'survey_id': 11}:
            self._results = [(11, 'john.smith@js.example', 123, 123, '2011-01-01')]
        elif 'count' in q:  # assume it's the sponsored query
            if 'some.one' in params.get('userid', ''):
                self._results = [(9, 3)]
            else:
                self._results = []
        else:
            self._results = []

        self._row = 0

    def fetchmany(self):
        return self._results

    def fetchall(self):
        return self._results

    def fetchone(self):
        row = self._results[self._row]
        self._row += 1
        return row

    def close(self):
        pass


def _integration_test(ini='integration-test.ini'):  # pragma nocover
    import datetime
    m = medcenter._integration_test()

    rt = config.RuntimeOptions(['survey_id'])
    rt.load(ini, 'saa_survey')
    return HeronRecords(setup_connection(ini),
                        m, datetime.date, int(rt.survey_id))


if __name__ == '__main__':  # pragma nocover
    import sys
    userid = sys.argv[1]
    hr = _integration_test()
    a = hr._m.affiliate(userid)
    q = hr.q_any(a)
    print "qualified?", q
    print hr.repositoryAccess(q)