'''redcapdb -- a little ORM support for REDCap's EAV structure
--------------------------------------------------------------

'''

import logging
import pkg_resources as pkg

import injector
from injector import inject, provides, singleton
from sqlalchemy import Table, Column, text
from sqlalchemy.engine.base import Connectable
from sqlalchemy.engine.url import URL
from sqlalchemy.types import INTEGER, VARCHAR, TEXT, DATETIME
from sqlalchemy.orm import mapper
from sqlalchemy.orm import session, sessionmaker
from sqlalchemy.sql import and_, select
from sqlalchemy.ext.declarative import declarative_base

import rtconfig
from ocap_file import Path
from sqlite_mem import _test_engine

log = logging.getLogger(__name__)
Base = declarative_base()
CONFIG_SECTION = 'redcapdb'

redcap_data = Table('redcap_data', Base.metadata,
                    Column(u'project_id', INTEGER(),
                           nullable=False, default=text(u"'0'"),
                           primary_key=True),
                    Column(u'event_id', INTEGER(), primary_key=True),
                    Column(u'record', VARCHAR(length=100), primary_key=True),
                    Column(u'field_name', VARCHAR(length=100),
                           primary_key=True),
                    Column(u'value', TEXT()),
                    )

# this is mostly for testing
redcap_surveys_response = Table('redcap_surveys_response', Base.metadata,
    Column(u'response_id', INTEGER(), primary_key=True, nullable=False),
            Column(u'participant_id', INTEGER()),
            Column(u'record', VARCHAR(length=100)),
            Column(u'first_submit_time', DATETIME()),
            Column(u'completion_time', DATETIME()),
            Column(u'return_code', VARCHAR(length=8)),
    )

redcap_surveys_participants = Table('redcap_surveys_participants',
                                    Base.metadata,
    Column(u'participant_id', INTEGER(), primary_key=True, nullable=False),
            Column(u'survey_id', INTEGER()),
            Column(u'event_id', INTEGER()),
            Column(u'hash', VARCHAR(length=6)),
            Column(u'legacy_hash', VARCHAR(length=32)),
            Column(u'participant_email', VARCHAR(length=255)),
            Column(u'participant_identifier', VARCHAR(length=255)),
    )


redcap_surveys = Table(
    'redcap_surveys',
    Base.metadata,
    Column(u'survey_id', INTEGER(), primary_key=True, nullable=False),
    Column(u'project_id', INTEGER()))


redcap_events_arms = Table(
    'redcap_events_arms',
    Base.metadata,
    Column(u'arm_id', INTEGER(), primary_key=True, nullable=False),
    Column(u'project_id', INTEGER()))


redcap_events_metadata = Table(
    'redcap_events_metadata',
    Base.metadata,
    Column(u'event_id', INTEGER(), primary_key=True, nullable=False),
    Column(u'arm_id', INTEGER()))


redcap_user_rights = Table(
    'redcap_user_rights', Base.metadata,
    Column('project_id', INTEGER),
    Column('username', VARCHAR))


def eachcol(t1, t2, cols):
    '''
      >>> pairs = eachcol(redcap_data, redcap_data,
      ...                 ['project_id', 'record'])
      >>> pairs[0][0].name
      u'project_id'
    '''
    # .columns is an OrderedDict, so we can correlate indexes.
    # oops... sqlalchemy.sql.expression.FromClause.corresponding_column
    # probably does this.
    n1 = t1.columns.keys()
    n2 = t2.columns.keys()
    return [(t1.columns[n1[n2.index(col)]], t2.columns[col])
            for col in cols]


def colsmatch(t1, t2, cols):
    '''
      >>> exp = colsmatch(redcap_data, redcap_data.alias('x2'),
      ...                 ['project_id', 'record'])
      >>> print exp
      redcap_data.project_id = x2.project_id AND redcap_data.record = x2.record

    '''
    return and_(*[(t1c == t2c) for t1c, t2c in eachcol(t1, t2, cols)])


def eav_join(t, keycols, attrs, acol, vcol):
    '''
      >>> cols1, j1, w1 = eav_join(redcap_data,
      ...                          ['project_id', 'record'],
      ...                          ['url'],
      ...                          'field_name', 'value')
      >>> cols1
      [Column(u'value', TEXT(), table=<j_url>)]

      >>> print select(cols1).where(w1)  # doctest: +NORMALIZE_WHITESPACE
      SELECT j_url.value
      FROM redcap_data AS j_url
      WHERE j_url.field_name = :field_name_1

      >>> c2, j2, w2 = eav_join(redcap_data,
      ...                       ['project_id', 'record'],
      ...                       ['url', 'name'],
      ...                       'field_name', 'value')
      >>> print select(c2).where(w2)
      ... # doctest: +NORMALIZE_WHITESPACE
      SELECT j_url.value, j_name.value FROM redcap_data AS j_url,
      redcap_data AS j_name WHERE j_url.field_name = :field_name_1 AND
      j_url.project_id = j_name.project_id AND j_url.record =
      j_name.record AND j_name.field_name = :field_name_2


      >>> c3, j3, w3 = eav_join(redcap_data,
      ...                       ['project_id', 'record'],
      ...                       ['disclaimer_id', 'url', 'current'],
      ...                       'field_name', 'value')
      >>> print select(c3).where(w3).apply_labels()
      ... # doctest: +NORMALIZE_WHITESPACE
      SELECT j_disclaimer_id.value AS j_disclaimer_id_value,
      j_url.value AS j_url_value, j_current.value AS j_current_value
      FROM redcap_data AS j_disclaimer_id, redcap_data AS j_url,
      redcap_data AS j_current WHERE j_disclaimer_id.field_name =
      :field_name_1 AND j_disclaimer_id.project_id = j_url.project_id
      AND j_disclaimer_id.record = j_url.record AND j_url.field_name =
      :field_name_2 AND j_disclaimer_id.project_id =
      j_current.project_id AND j_disclaimer_id.record =
      j_current.record AND j_current.field_name = :field_name_3
      '''

    #aliases = dict([(n, t.alias('t_' + n)) for n in attrs])

    # use itertools rather than for loop for fold?
    #a0 = aliases[attrs[0]]
    t0 = t.alias('j_' + attrs[0])
    product = t0
    where = t0.columns[acol] == attrs[0]
    vcols = [t0.columns[vcol]]

    for n in attrs[1:]:
        tn = t.alias('j_' + n)
        wn = colsmatch(product, tn, keycols)
        where = and_(where, wn, (tn.columns[acol] == n))
        product = product.join(tn, wn)
        vcols.append(tn.columns[vcol])

    return vcols, product, where


class REDCapRecord(object):
    '''Abstract class that provides mapping of fields to redcap EAV structure.

    For testing, we'll use the example from import_records.php
    from REDCap API examples::
      >>> _TestRecord.fields
      ('study_id', 'age', 'sex')

    '''

    fields = ()

    def __repr__(self):
        '''
          >>> r = _TestRecord('test_001', 31, 0)
          >>> r
          _TestRecord(study_id=test_001, age=31, sex=0)
        '''
        return self.__class__.__name__ + '(' + (
            ', '.join(['%s=%s' % (f, getattr(self, f))
                       for f in self.fields])) + ')'

    @classmethod
    def eav_map(cls, project_id, alias='eav'):
        '''Set up the ORM mapping based on project_id.

        :param cls: class to map
        :param pid: redcap project id to select
        :param fields: 1st is primary key
        :returns: (value_columns, join_where_clause)

        For example::

          >>> cols, where = _TestRecord.eav_map(project_id=123)
          >>> [c.table.name for c in cols]
          ['j_study_id', 'j_age', 'j_sex']
          >>> str(where)
          ... # doctest: +NORMALIZE_WHITESPACE
          'j_study_id.field_name = :field_name_1 AND
          j_study_id.project_id = j_age.project_id AND
          j_study_id.record = j_age.record AND j_age.field_name =
          :field_name_2 AND j_study_id.project_id = j_sex.project_id
          AND j_study_id.record = j_sex.record AND j_sex.field_name =
          :field_name_3'

          >>> (smaker, ) = Mock.make([(session.Session,
          ...                          CONFIG_SECTION)])
          >>> s = smaker()
          >>> for project_id, record, field_name, value in (
          ...     (123, 1, 'study_id', 'test_002'),
          ...     (123, 1, 'age', 32),
          ...     (123, 1, 'sex', 1)):
          ...     s.execute(redcap_data.insert().values(
          ...                 event_id=321,
          ...                 project_id=project_id, record=record,
          ...                 field_name=field_name, value=value)) and None
          >>> s.commit()
          >>> s.query(_TestRecord).all()
          [_TestRecord(study_id=test_002, age=32, sex=1)]

        '''
        data = redcap_data.select().where(
            redcap_data.c.project_id == project_id)
        cols, j, w = eav_join(data.alias(alias),
                              keycols=('project_id', 'record'),
                              attrs=cls.fields,
                              acol='field_name', vcol='value')

        mapper(cls, select(cols).where(w).apply_labels().alias(),
               primary_key=[cols[0]],
               properties=dict(zip(cls.fields, cols)))

        return cols, w


class _TestRecord(REDCapRecord):
    fields = ('study_id', 'age', 'sex')

    def __init__(self, study_id, age, sex):
        self.study_id = study_id
        self.age = age
        self.sex = sex


def allfields(ex, project_id, record):
    '''Iterate over all fields in a REDCap record.

    :param ex: a SQLA executable (engine, session, ...)
    :param project_id: to match redcap_data
    :param record: to match redcap_data
    :return: an iterator over (k, v) pairs

    For example::

      >>> (smaker, ) = Mock.make([(session.Session,
      ...                          CONFIG_SECTION)])
      >>> s = smaker()
      >>> for k, v in (('study_id', 'test_002'), ('age', 32)):
      ...     s.execute(redcap_data.insert().values(event_id=321,
      ...                                           project_id=1234,
      ...                                           record=1,
      ...                                           field_name=k,
      ...                                           value=v)) and None

      >>> list(allfields(s, 1234, 1))
      [(u'age', u'32'), (u'study_id', u'test_002')]
    '''
    c = redcap_data.c
    for k, v in ex.execute(select((c.field_name, c.value))
                           .where(and_(c.project_id == project_id,
                                       c.record == record))).fetchall():
        yield k, v


class SetUp(injector.Module):
    # abusing Session a bit; this really provides a subclass,
    # not an instance, of Session
    @provides((session.Session, CONFIG_SECTION))
    @inject(engine=(Connectable, CONFIG_SECTION))
    def redcap_sessionmaker(self, engine):
        return sessionmaker(engine)


class Mock(injector.Module, rtconfig.MockMixin):
    sql = pkg.resource_string(__name__, 'mock_redcapdb.sql').split(';\n')

    @singleton
    @provides((Connectable, CONFIG_SECTION))
    def redcap_datasource(self):
        # import logging  # @@ lazy
        # log = logging.getLogger(__name__)
        # salog = logging.getLogger('sqlalchemy.engine.base.Engine')
        # salog.setLevel(logging.INFO)
        # log.debug('redcap create_engine: again?')
        e = _test_engine()
        self.init_db(e)
        return e

    @classmethod
    def init_db(cls, e):
        salog = logging.getLogger('sqlalchemy.engine.base.Engine')
        old = salog.level
        salog.setLevel(logging.WARN)
        work = e.connect()
        for sql in Mock.sql:
            # avoid "cannot start a transaction within a transaction"
            if sql in ['', 'BEGIN TRANSACTION', 'COMMIT']:
                continue
            work.execute(sql)
        work.close()
        salog.setLevel(old)

    @classmethod
    def engine(cls):
        # Mock support without the injector overhead
        engine = _test_engine()
        cls.init_db(engine)
        return engine

    @classmethod
    def mods(cls):
        return [cls(), SetUp()]


def add_test_eav(s, project_id, event_id, e, avs):
    log.debug('add_test_eav: %s', (project_id, event_id, e, avs))
    for a, v in avs:
        s.execute(redcap_data.insert().values(
                project_id=project_id, event_id=event_id,
                record=e, field_name=a, value=v))


class RunTime(rtconfig.IniModule):  # pragma: nocover
    def __init__(self, ini, create_engine):
        rtconfig.IniModule.__init__(self, ini)
        # TODO: factor create_engine handling out to rtconfig?
        self.__create_engine = create_engine

    @provides((rtconfig.Options, CONFIG_SECTION))
    def opts(self):
        return self.get_options(
            'user password host port database engine'.split(),
            CONFIG_SECTION)

    @singleton
    @provides((Connectable, CONFIG_SECTION))
    @inject(rt=(rtconfig.Options, CONFIG_SECTION))
    def redcap_datasource(self, rt, driver='mysql+mysqldb'):
        # support sqlite3 driver?
        u = (rt.engine if rt.engine else
             URL(driver, rt.user, rt.password,
                 rt.host, rt.port, rt.database))

        # http://www.sqlalchemy.org/docs/dialects/mysql.html
        #      #connection-timeouts
        return self.__create_engine(u, pool_recycle=3600)

    @classmethod
    def mods(cls, ini, create_engine, **kwargs):
        return [cls(ini, create_engine), SetUp()]


if __name__ == '__main__':  # pragma: nocover
    def _integration_test():  # pragma: nocover
        '''Print distinct field_name from a given project_id.
        '''
        from io import open as io_open
        from os.path import join as path_join, exists as path_exists
        from pprint import pprint
        from sys import argv

        from sqlalchemy import create_engine

        project_id = int(argv[-1])

        cwd = Path('.', (io_open, path_join, path_exists))

        [sm] = RunTime.make([(session.Session, CONFIG_SECTION)],
                            ini=cwd / 'integration-test.ini',
                            create_engine=create_engine)
        s = sm()
        print("slice of redcap_data:")
        pprint(s.query(redcap_data).slice(1, 10))
        pprint(s.query(redcap_data).slice(1, 10).all())

        print("field_name list:")
        ans = s.execute(select([redcap_data.c.field_name], distinct=True)
                        .where(redcap_data.c.project_id == project_id))
        pprint(ans.fetchall())

        print("users:")
        ans = s.execute(select([redcap_user_rights.c.username], distinct=True)
                        .where(redcap_user_rights.c.project_id == project_id))
        pprint(ans.fetchall())

    _integration_test()
