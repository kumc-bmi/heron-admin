'''i2b2metadata -- I2B2 project REDCap terms
-------------------------------------------------------------
'''

import logging
from sqlalchemy import text

log = logging.getLogger(__name__)


class i2b2Metadata():
    def __init__(self):
        pass

    def project_terms(self, i2b2_pid, rc_pids, proj_desc, mdsm):
        '''create heron_terms and table_access views in the chosen i2b2 project
        '''
        #Example i2b2_pid: REDCap_24
        pid = i2b2_pid.split('_')[1]

        #http://stackoverflow.com/questions/2179493/
        #... adding-backslashes-without-escaping-python
        sql_ht = '''CREATE OR REPLACE VIEW
    REDCAPMETADATA''' + pid + '''.HERON_TERMS AS
    SELECT * FROM BLUEHERONMETADATA.HERON_TERMS
    UNION ALL
    SELECT * FROM BLUEHERONMETADATA.REDCAP_TERMS
    where C_FULLNAME='\\i2b2\\redcap\\\''''
        for rc_pid in rc_pids:
            sql_ht += ''' UNION ALL
    SELECT * FROM BLUEHERONMETADATA.REDCAP_TERMS
    WHERE C_FULLNAME LIKE \'\\i2b2\\redcap\\''' + rc_pid + '''%\''''
        mdsm.execute(sql_ht)

    def revoke_access(self, i2b2_pid, default_pid):
        '''Revoke user access to a project that will be re-purposed
        '''
        sql_revoke = text('''update i2b2pm.pm_project_user_roles
        set project_id = :def_pid
        where project_id = :pid''')
        self._ds.execute(sql_revoke, def_pid=default_pid, pid=i2b2_pid)

    def rc_in_i2b2(self, rc_pids, mdsm):
        '''return true if data from atleast one rc_pid is in HERON
        '''
        for rc_pid in rc_pids:
            c_fullname = '\\i2b2\\redcap\\' + str(rc_pid) + '\\%'
            sql = text('''select * from blueheronmetadata.redcap_terms
where c_hlevel = 2 and c_fullname LIKE :cfn''')
            if mdsm.execute(sql, cfn=c_fullname):
                return True
        return False


class MockMetadata():
    def __init__(self, i):
        self.i = i

    def rc_in_i2b2(self, pids):
        return self.i

    def project_terms(self, i2b2_pid,
                         rc_pids, proj_desc, mdsm):
        return True
