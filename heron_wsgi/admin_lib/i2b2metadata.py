'''i2b2metadata -- Metadata for I2B2 REDCap projects
----------------------------------------------------
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
        self._mdsm = metadatasm

    def project_terms(self, i2b2_pid, rc_pids):
        '''Create heron_terms view in the chosen i2b2 project.
        '''
        log.debug('Creating heron_terms for %s with redcap pids: %s',
                  i2b2_pid, str(rc_pids))
        mds = self._mdsm()

        pid, schema = schema_for(i2b2_pid)
        #http://stackoverflow.com/questions/2179493/
        #... adding-backslashes-without-escaping-python

        #TODO: Separate redcap_terms from heron_terms
        #... and insert only redcap_terms
        mds.execute('''DELETE FROM %s.HERON_TERMS''' % schema)

        insert_cmd, params = insert_for(pid, schema, rc_pids)
        mds.execute(insert_cmd, params)

        mds.commit()

    def rc_in_i2b2(self, rc_pids):
        """Find out which REDCap projects are in HERON.

        :return: subset of rc_pids that have corresponding terms
                 in blueheronmetadata.
        """
        mds = self._mdsm()

        terms = mds.execute(text(r"""select c_fullname
        from blueheronmetadata.redcap_terms
        where c_hlevel = 2
        and c_fullname LIKE
        '\i2b2\redcap\%\'
        """)).fetchall()

        return [t.c_fullname for t in terms
                if t.c_fullname in rc_pids]


def insert_for(pid, schema, rc_pids):
    r"""
    >>> sql, params = insert_for('24', 'REDCAPMETADATA24', [])
    >>> params
    {}
    >>> print sql  # doctest: +NORMALIZE_WHITESPACE
    INSERT INTO REDCAPMETADATA24.HERON_TERMS
    SELECT * FROM BLUEHERONMETADATA.HERON_TERMS UNION ALL
    SELECT * FROM BLUEHERONMETADATA.REDCAP_TERMS
        where C_FULLNAME='\i2b2\redcap\'

    >>> sql, params = insert_for('24', 'REDCAPMETADATA24', [10, 20, 30])
    >>> sorted(params.items())
    [(':pid0', 10), (':pid1', 20), (':pid2', 30)]
    >>> print sql  # doctest: +NORMALIZE_WHITESPACE
    INSERT INTO REDCAPMETADATA24.HERON_TERMS
    SELECT * FROM BLUEHERONMETADATA.HERON_TERMS UNION ALL
    SELECT * FROM BLUEHERONMETADATA.REDCAP_TERMS
        where C_FULLNAME='\i2b2\redcap\'  UNION ALL
    SELECT * FROM BLUEHERONMETADATA.REDCAP_TERMS
            WHERE C_FULLNAME LIKE '\i2b2\redcap\' || :pid2 || \%\  UNION ALL
    SELECT * FROM BLUEHERONMETADATA.REDCAP_TERMS
            WHERE C_FULLNAME LIKE '\i2b2\redcap\' || :pid0 || \%\  UNION ALL
    SELECT * FROM BLUEHERONMETADATA.REDCAP_TERMS
            WHERE C_FULLNAME LIKE '\i2b2\redcap\' || :pid1 || \%\
    """

    params = dict([(':pid%d' % ix, pid)
                   for (ix, pid) in enumerate(rc_pids)])
    clauses = [
        r"""SELECT * FROM BLUEHERONMETADATA.REDCAP_TERMS
        WHERE C_FULLNAME LIKE '\i2b2\redcap\' || %s || \%%\ """ % pname
        for pname in params.keys()]

    sql = ("INSERT INTO %s.HERON_TERMS\n" % schema) + ' UNION ALL\n'.join([
    r"""SELECT * FROM BLUEHERONMETADATA.HERON_TERMS""",
    r"""SELECT * FROM BLUEHERONMETADATA.REDCAP_TERMS
    where C_FULLNAME='\i2b2\redcap\' """] + clauses)

    return sql, params


def schema_for(i2b2_pid):
    '''Build schema name from specially formatted HERON project ID.

    See also create_redcap_projects task in heron_build.py

    >>> schema_for("REDCap_24")
    ('24', 'REDCAPMETADATA24')
    '''
    pid = i2b2_pid.split('_')[1]
    return pid, 'REDCAPMETADATA' + i2b2_pid.split('_')[1]


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
