'''i2b2metadata -- Metadata for I2B2 REDCap projects
----------------------------------------------------
'''

import logging

import injector
from injector import inject, provides, singleton
from sqlalchemy import text, orm, Table, MetaData

import rtconfig
import ocap_file


log = logging.getLogger(__name__)

CONFIG_SECTION_MD = 'i2b2md'
Ki2b2meta_schema = injector.Key('i2b2meta_schema')


class I2B2Metadata(ocap_file.Token):
    @inject(metadatasm=(orm.session.Session, CONFIG_SECTION_MD),
            i2b2meta_schema=Ki2b2meta_schema)
    def __init__(self, metadatasm, i2b2meta_schema):
        '''
        :param metadatasm: a function that returns an sqlalchemy session
        '''
        self._mdsm = metadatasm
        self.i2b2meta_schema = i2b2meta_schema

    def project_terms(self, i2b2_pid, rc_pids,
                      rct_table='REDCAP_TERMS'):
        '''Create heron_terms view in the chosen i2b2 project.
        '''
        mds = self._mdsm()

        pid, schema = schema_for(i2b2_pid, self.i2b2meta_schema)
        log.info('Updating redcap_terms for %s (%s) with redcap pids: %s',
                 i2b2_pid, schema, rc_pids)
        # http://stackoverflow.com/questions/2179493/
        # ... adding-backslashes-without-escaping-python

        # TODO: Separate redcap_terms from heron_terms
        # ... and insert only redcap_terms
        mds.execute('''DELETE FROM %s.%s''' % (schema, rct_table))

        rct = Table(rct_table, MetaData(), schema=schema, autoload=True,
                    autoload_with=mds.bind)

        insert_cmd, params = insert_for(self.i2b2meta_schema, pid, schema,
                                        rc_pids,
                                        [c.name for c in rct.columns])

        log.debug('insert_cmd: %s', insert_cmd)
        mds.execute(text(insert_cmd), params=params)

        mds.commit()

    def rc_in_i2b2(self, rc_pids):
        """Find out which REDCap projects are in HERON.

        :return: subset of rc_pids that have corresponding terms
                 in blueheronmetadata.
        """
        try:
            mds = self._mdsm()
        except Exception as ex:
            log.error('rc_in_i2b2 failed to connect', exc_info=ex)
            return []

        terms = mds.execute(text(r"""select c_fullname
        from %s.REDCAP_TERMS_ENHANCED
        where c_hlevel = 2
        and c_fullname LIKE
        '\i2b2\redcap\%%\'
        """ % self.i2b2meta_schema)).fetchall()

        term_ids = [int(t.c_fullname.split('\\')[3])
                    for t in terms]
        log.info('REDCap project terms: %s', term_ids)
        return [pid for pid in rc_pids
                if pid in term_ids]


def insert_for(i2b2meta_schema, pid, schema, rc_pids, cols):
    r"""
    >>> sql, params = insert_for(
    ...     'BLUEHERONMETADATA', '24', 'REDCAPMETADATA24', [10, 20, 30],
    ...     ['c1', 'c2'])
    >>> sorted(params.items())
    [('pid0', 10), ('pid1', 20), ('pid2', 30)]
    >>> print sql  # doctest: +NORMALIZE_WHITESPACE
    INSERT INTO REDCAPMETADATA24.REDCAP_TERMS (c1,c2)
    SELECT c1,c2 FROM BLUEHERONMETADATA.REDCAP_TERMS_ENHANCED
                   where C_FULLNAME='\i2b2\redcap\'  UNION ALL
    SELECT c1,c2 FROM BLUEHERONMETADATA.REDCAP_TERMS_ENHANCED
            WHERE C_FULLNAME LIKE ('\i2b2\redcap\' || :pid0 || '\%')  UNION ALL
    SELECT c1,c2 FROM BLUEHERONMETADATA.REDCAP_TERMS_ENHANCED
            WHERE C_FULLNAME LIKE ('\i2b2\redcap\' || :pid1 || '\%')  UNION ALL
    SELECT c1,c2 FROM BLUEHERONMETADATA.REDCAP_TERMS_ENHANCED
            WHERE C_FULLNAME LIKE ('\i2b2\redcap\' || :pid2 || '\%')
    """
    assert rc_pids
    params = dict([('pid%d' % ix, p)
                   for (ix, p) in enumerate(rc_pids)])
    cv = ','.join(cols)
    clauses = [
        r"""SELECT %s FROM %s.REDCAP_TERMS_ENHANCED
        WHERE C_FULLNAME LIKE ('\i2b2\redcap\' || :%s || '\%%') """ %
        (cv, i2b2meta_schema, pname) for pname in sorted(params.keys())]

    sql = ("INSERT INTO %s.REDCAP_TERMS (%s)\n" % (schema, cv) +
           ' UNION ALL\n'.join([
               r"""SELECT %s FROM %s.REDCAP_TERMS_ENHANCED
               where C_FULLNAME='\i2b2\redcap\' """ % (','.join(cols),
                                                       i2b2meta_schema)] +
                               clauses))

    return sql, params


def flipflop_suffix(i2b2meta_schema):
    '''Figure flip-flop context from externally provided i2b2meta_schema.

    >>> flipflop_suffix("bhmetadataB2")
    'B2'

    '''

    suffix = i2b2meta_schema[-2:].upper()
    assert suffix in ("A1", "B2")
    return suffix


def schema_for(i2b2_pid, i2b2meta_schema):
    '''Build schema name from specially formatted HERON project ID.

    See also create_redcap_projects task in heron_build.py

    >>> schema_for("REDCap_24", "bhmetadataB2")
    ('24', 'REDCAPMETADATA24B2')
    '''
    pid = i2b2_pid.split('_')[1]
    flipflop = flipflop_suffix(i2b2meta_schema)
    return pid, 'REDCAPMETADATA' + i2b2_pid.split('_')[1] + flipflop


class MockMetadata():
    '''Mock up I2B2Metadata.
    '''
    def __init__(self, i):
        self.i = i

    def rc_in_i2b2(self, pids):
        '''Every other REDCap project is loaded in i2b2
        '''
        return pids[::2]

    def project_terms(self, i2b2_pid, rc_pids):
        pass


class RunTime(rtconfig.IniModule):
    jndi_name_md = 'java:/i2b2REDCapMgrDS'

    def __init__(self, ini, create_engine):
        rtconfig.IniModule.__init__(self, ini)

    @singleton
    @provides((orm.session.Session, CONFIG_SECTION_MD))
    def md_sessionmaker(self):
        def send_sessionmaker():
            sm = orm.session.sessionmaker()
            engine = self.get_options(['i2b2meta_url'], CONFIG_SECTION_MD)
            ds = sm(bind=engine)
            return ds
        return send_sessionmaker

    @provides(Ki2b2meta_schema)
    def i2b2meta_schema(self):
        rt = self.get_options(['i2b2meta_schema'], CONFIG_SECTION_MD)
        meta_schema = rt.i2b2meta_schema
        log.info('i2b2meta_schema: %s', meta_schema)
        return meta_schema

    @classmethod
    def mods(cls, ini, create_engine):
        return [cls(ini=ini, create_engine=create_engine)]


if __name__ == '__main__':
    def _integration_test():
        # e.g. python i2b2metadata.py REDCap_1 10,11,53,55
        from sys import argv
        from io import open as io_open
        import os

        from sqlalchemy import create_engine

        logging.basicConfig(level=logging.DEBUG)
        salog = logging.getLogger('sqlalchemy.engine.base.Engine')
        salog.setLevel(logging.INFO)

        i2b2_pid, rc_pids = argv[1:3]

        cwd = ocap_file.Path('.',
                             open=io_open,
                             joinpath=os.path.join,
                             listdir=os.listdir,
                             exists=os.path.exists)
        [md] = RunTime.make([I2B2Metadata],
                            ini=cwd / 'integration-test.ini',
                            create_engine=create_engine)
        t = md.rc_in_i2b2(rc_pids.split(','))
        print(md.project_terms('META', i2b2_pid, t))

    _integration_test()
