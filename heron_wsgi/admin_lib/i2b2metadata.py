'''i2b2metadata -- I2B2 project REDCap terms
-------------------------------------------------------------
'''

import logging
from sqlalchemy import text, orm
import injector
from injector import inject, provides, singleton

import rtconfig
import jndi_util
import ocap_file

log = logging.getLogger(__name__)

CONFIG_SECTION_MD = 'i2b2pm'


class i2b2Metadata(ocap_file.Token):
    @inject(metadatasm=(orm.session.Session, CONFIG_SECTION_MD))
    def __init__(self, metadatasm):
        self.mdsm = metadatasm()

    def project_terms(self, i2b2_pid, rc_pids):
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
    WHERE C_FULLNAME LIKE \'\\i2b2\\redcap\\''' + str(rc_pid) + '''%\''''
        self.mdsm.execute(sql_ht)

    def revoke_access(self, i2b2_pid, default_pid):
        '''Revoke user access to a project that will be re-purposed
        '''
        sql_revoke = text('''update i2b2pm.pm_project_user_roles
        set project_id = :def_pid
        where project_id = :pid''')
        self._ds.execute(sql_revoke, def_pid=default_pid, pid=i2b2_pid)

    def rc_in_i2b2(self, rc_pids):
        '''return true if data from atleast one rc_pid is in HERON
        '''
        pid_lst = []
        for rc_pid in rc_pids:
            c_fullname = '\\i2b2\\redcap\\' + str(rc_pid) + '\\%'
            sql = text('''select * from blueheronmetadata.redcap_terms
where c_hlevel = 2 and c_fullname LIKE :cfn and rownum=1''')
            if self.mdsm.execute(sql, params=dict(cfn=c_fullname)):
                log.debug('Data from REDCap pid: %s is in HERON', rc_pid)
                pid_lst.append(rc_pid)
        return pid_lst if pid_lst else False


class MockMetadata():
    def __init__(self, i):
        self.i = i

    def rc_in_i2b2(self, pids):
        return  pids[::2]

    def project_terms(self, i2b2_pid,
                         rc_pids):
        return True


class RunTime(rtconfig.IniModule):
    #From i2b2pm.py
    jndi_name_md = 'i2b2REDCapMgrDS'

    @singleton
    @provides((orm.session.Session, CONFIG_SECTION_MD))
    def sessionmaker(self):
        import os
        from sqlalchemy import create_engine
        rt = rtconfig.RuntimeOptions(['jboss_deploy'])
        rt.load(self._ini, CONFIG_SECTION_MD)
        jdir = ocap_file.Readable(rt.jboss_deploy, os.path, os.listdir, open)
        sm = orm.session.sessionmaker()
        engine = jndi_util.JBossContext(jdir,
                    create_engine).lookup(self.jndi_name_md)
        ds = sm(bind=engine)
        return ds
