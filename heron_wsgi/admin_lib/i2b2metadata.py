'''i2b2metadata -- Metadata for I2B2 REDCap projects
-------------------------------------------------------------
'''

import logging
from sqlalchemy import text, orm
from injector import inject, provides, singleton

import rtconfig
import jndi_util
import ocap_file

log = logging.getLogger(__name__)

CONFIG_SECTION_MD = 'i2b2md'


class I2B2Metadata(ocap_file.Token):
    @inject(metadatasm=(orm.session.Session, CONFIG_SECTION_MD))
    def __init__(self, metadatasm):
        '''
        :param metadatasm: a function that returns an sqlalchemy session
        '''
        self._mds = metadatasm

    def project_terms(self, i2b2_pid, rc_pids):
        '''Create heron_terms view in the chosen i2b2 project.
        '''
        log.debug('Creating heron_terms for %s with redcap pids: %s',
                  i2b2_pid, str(rc_pids))
        mds = self._mds()
        #Example i2b2_pid: REDCap_24
        pid = i2b2_pid.split('_')[1]
        #http://stackoverflow.com/questions/2179493/
        #... adding-backslashes-without-escaping-python

        #TODO: Separate redcap_terms from heron_terms
        #... and insert only redcap_terms
        sql_dl = '''DELETE FROM
        REDCAPMETADATA''' + pid + '''.HERON_TERMS'''
        mds.execute(sql_dl)

        sql_ht = '''INSERT INTO
    REDCAPMETADATA''' + pid + '''.HERON_TERMS
    SELECT * FROM BLUEHERONMETADATA.HERON_TERMS
    UNION ALL
    SELECT * FROM BLUEHERONMETADATA.REDCAP_TERMS
    where C_FULLNAME='\\i2b2\\redcap\\\''''
        for rc_pid in rc_pids:
            sql_ht += ''' UNION ALL
    SELECT * FROM BLUEHERONMETADATA.REDCAP_TERMS
    WHERE C_FULLNAME LIKE \'\\i2b2\\redcap\\''' + str(rc_pid) + '''%\''''
        mds.execute(sql_ht)
        try:
            sql_im = '''CREATE INDEX
        REDCAPMETADATA1.META_FULLNAME_REDCAP_IDX
        ON REDCAPMETADATA1.HERON_TERMS (C_FULLNAME)
        TABLESPACE bheron_indexes'''
            #mds.execute(sql_im)

            sql_ia = '''CREATE INDEX
        REDCAPMETADATA1.META_APPLIED_PATH_REDCAP_IDX
        ON REDCAPMETADATA1.HERON_TERMS (M_APPLIED_PATH)
        TABLESPACE bheron_indexes'''
            #mds.execute(sql_ia)

            mds.commit
            return True
        except:
            return False

    def revoke_access(self, i2b2_pid, default_pid):
        '''Revoke user access to a project that will be re-purposed.
        #TODO: Retire this
        '''
        mds = self._mds()
        sql_revoke = text('''update i2b2pm.pm_project_user_roles
        set project_id = :def_pid
        where project_id = :pid''')
        mds.execute(sql_revoke, def_pid=default_pid, pid=i2b2_pid)

    def rc_in_i2b2(self, rc_pids):
        '''Return pids of REDCap projects that have been loaded into HERON.
        '''
        mds = self._mds()
        pid_lst = []
        for rc_pid in rc_pids:
            c_fullname = '\\i2b2\\redcap\\' + str(rc_pid) + '\\%'
            sql = text('''select * from blueheronmetadata.redcap_terms
where c_hlevel = 2 and c_fullname LIKE :cfn and rownum=1''')
            if mds.execute(sql, params=dict(cfn=c_fullname)).fetchall():
                log.debug('Data from REDCap pid: %s is in HERON', rc_pid)
                pid_lst.append(rc_pid)
        return pid_lst if pid_lst else False


class MockMetadata():
    '''Mock up I2B2Metadata.
    '''
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

    def sessionmaker(self, jndi, CONFIG):
        import os
        from sqlalchemy import create_engine

        rt = rtconfig.RuntimeOptions(['jboss_deploy'])
        rt.load(self._ini, CONFIG)

        jdir = ocap_file.Readable(rt.jboss_deploy, os.path, os.listdir, open)
        ctx = jndi_util.JBossContext(jdir, create_engine)

        def send_sessionmaker():
            sm = orm.session.sessionmaker()
            engine = ctx.lookup(jndi)
            ds = sm(bind=engine)
            return ds
        return send_sessionmaker

    @singleton
    @provides((orm.session.Session, CONFIG_SECTION_MD))
    def md_sessionmaker(self):
        return self.sessionmaker(self.jndi_name_md, CONFIG_SECTION_MD)


def _integration_test():
    #e.g. python i2b2metadata.py REDCap_1 10,11,53,55
    import sys

    logging.basicConfig(level=logging.DEBUG)
    salog = logging.getLogger('sqlalchemy.engine.base.Engine')
    salog.setLevel(logging.INFO)

    i2b2_pid, rc_pids = sys.argv[1:3]

    (md, ) = RunTime.make(None, [I2B2Metadata])
    t = md.rc_in_i2b2(rc_pids.split(','))
    print md.project_terms(i2b2_pid, t)


if __name__ == '__main__':
    _integration_test()
