'''heron_policy.py -- HERON policy decisions, records
'''

from db_util import transaction, connect
import config

class HeronRecords(object):
    # TODO: connection pooling/management?
    def __init__(self, conn):
        self._conn = conn

    def is_executive(self, agent):
        with transaction(self._conn) as q:
            q.execute('''select count(*)
                         from heron.exec_group where user_id=:u
		         and status ='A' ''', {'u': agent.userid()})
            return q.fetchone()[0] > 0

def setup_connection(ini='heron_records.ini', section='heron'):
    ro = config.RuntimeOptions('user password host port sid')
    ro.load(ini, section)
    return connect(ro.user, ro.password, ro.host, ro.port or 1521, ro.sid)

def _integration_test():
    return HeronRecords(setup_connection())

if __name__ == '__main__':
    import sys
    userid = sys.argv[1]
    hr = _integration_test()
    import medcenter
    m = medcenter._integration_test()
    print "%s is executive? %s" % (
        userid, hr.is_executive(m.affiliate(userid)))
