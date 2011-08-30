'''heron_policy.py -- HERON policy decisions, records
'''

from db_util import transaction, connect
import config

import medcenter

class HeronRecords(object):
    # TODO: connection pooling/management?
    def __init__(self, conn, medcenter, timesrc):
        self._conn = conn
        self._m = medcenter
        self._t = timesrc

    def saa_signed(self, agent):
        return self._agent_test('''select 1 as tot
                         from heron.system_access_users
                          where user_id=:u''', 'u', agent)

    def q_executive(self, agent):
        if not self._agent_test('''select 1
                         from heron.exec_group where user_id=:u
		         and status ='A' ''', 'u', agent):
            raise NotExecutive()
        return OK(agent)

    def q_faculty(self, agent):
        self._m.checkFaculty(agent)
        return OK(agent)

    def q_sponsored(self, agent):
        # TODO: normalize database using org table
        if not self._agent_test(
            '''select user_id
               from heron.SPONSORSHIP
               where user_id=:u
	         and (expire_date is null or expire_date>sysdate)
                 and access_type='VIEW_ONLY' 
                 and (kuh_approval_status ='A'
                      and kumc_approval_status ='A'
                      and ukp_approval_status ='A')''', 'u', agent):
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
        texp = self._m.trainedThru(a)
        if texp is None:
            raise NoTraining("no training on file")
        if texp < self._t.today().isoformat():
            raise NoTraining("training out of date")
        if not self.saa_signed(a):
            raise NoAgreement()
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
    def __init__(self, agent):
        self._agent = agent

def setup_connection(ini='heron_records.ini', section='heron'):
    ro = config.RuntimeOptions('user password host port sid')
    ro.load(ini, section)
    return connect(ro.user, ro.password, ro.host, ro.port or 1521, ro.sid)


def _integration_test():
    import datetime
    m = medcenter._integration_test()
    return HeronRecords(setup_connection(), m, datetime.date)


if __name__ == '__main__':
    import sys
    userid = sys.argv[1]
    hr = _integration_test()
    a = hr._m.affiliate(userid)
    q = hr.q_any(a)
    print "qualified?", q
    print hr.repositoryAccess(q)
