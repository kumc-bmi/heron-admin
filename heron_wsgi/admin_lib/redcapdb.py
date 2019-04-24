'''redcapdb -- a little ORM support for REDCap's EAV structure
--------------------------------------------------------------

The redcap_data table is a "long skinny" EAV structure:

  project_id record_id field_name value
  4688       123       study_id   x23
  4688       123       age        42
  4688       123       sex        M

It's often more convenient to use row-modelling, a la a spreadsheet:

  record_id  study_id  age  sex
  123        x23        42   M

The `unpivot()` function helps::

    >>> cs, fs, wc, rel = unpivot(['study_id', 'age', 'sex'], record=True)
    >>> print(rel)
    ... # doctest: +NORMALIZE_WHITESPACE
    SELECT j_study_id.project_id,
           j_study_id.record,
           j_study_id.value AS study_id,
           j_age.value AS age,
           j_sex.value AS sex
    FROM redcap_data AS j_study_id, redcap_data AS j_age, redcap_data AS j_sex
    WHERE j_study_id.project_id = j_study_id.project_id
      AND j_study_id.field_name = :field_name_1
      AND j_age.project_id = j_study_id.project_id
      AND j_age.field_name = :field_name_2
      AND j_sex.project_id = j_study_id.project_id
      AND j_sex.field_name = :field_name_3
      AND j_study_id.record = j_age.record
      AND j_age.record = j_sex.record


    The first two columns work like a primary key:
      >>> [c.name for c in cs[:2]]
      ['project_id', 'record']

    The rest are the redcap fields:
      >>> [c.name for c in cs[2:]]
      ['study_id', 'age', 'sex']

    Each of the self-joins is named:
      >>> [r.name for r in fs]
      ['j_study_id', 'j_age', 'j_sex']


ISSUE: refactor w.r.t. traincheck.redcapview

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
      'project_id'
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


def unpivot(field_names,
            pfx='j_',
            record=False,
            redcap_data=redcap_data):
    '''Self-join redcap_data to unpivot EAV to row-modelling.
    '''
    if not field_names:
        raise ValueError(field_names)

    froms = [(n, redcap_data.alias(pfx + n)) for n in field_names]
    d0 = froms[0]  # 0th redcap_data table
    project_id = d0[1].c.project_id
    cols = [project_id] + ([d0[1].c.record] if record else []) + [
        frm.c.value.label(n) for (n, frm) in froms]

    project = [clause for (n, frm) in froms
               for clause in
               [frm.c.project_id == project_id,
                frm.c.field_name == n]]
    join = [froms[ix][1].c.record == froms[ix + 1][1].c.record
            for ix in range(len(froms) - 1)]

    w = and_(*project + join)
    from_obj = [f for (n, f) in froms]
    relation = select(cols, w, from_obj=from_obj)
    return cols, from_obj, w, relation


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
          >>> r = _TestRecord(123, '1', 'test_001', 31, 0)
          >>> r  # doctest: +NORMALIZE_WHITESPACE
          _TestRecord(project_id=123, record=1,
                      study_id=test_001, age=31, sex=0)
        '''
        info = [(f, getattr(self, f))
                for f in (('project_id', 'record') + self.fields)]
        return self.__class__.__name__ + '(' + (
            ', '.join(['%s=%s' % fv for fv in info])) + ')'

    @classmethod
    def eav_map(cls, alias='eav'):
        '''Set up the ORM mapping based on project_id.

        For example, suppose the DB has the following data::

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

       We can use the ORM as follows::

          >>> _ = _TestRecord.eav_map()
          >>> r = s.query(_TestRecord).filter(
          ...     _TestRecord.project_id == 123).first()
          >>> (r.study_id, r.age, r.sex)
          (u'test_002', u'32', u'1')

        '''
        cols, f, w, relation = unpivot(cls.fields,
                                       record=True, redcap_data=redcap_data)

        mapper(cls, relation.apply_labels().alias(),
               primary_key=cols[:2],
               properties=dict(dict(zip(cls.fields, cols[2:])),
                               project_id=cols[0], record=cols[1]))

        return cols, f, w


class _TestRecord(REDCapRecord):
    fields = ('study_id', 'age', 'sex')

    def __init__(self, project_id, record, study_id, age, sex):
        self.project_id = project_id
        self.record = record
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


def add_mock_eav(s, project_id, event_id, e, avs):
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
    def redcap_datasource(self, rt, driver='mysql+pymysql'):
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

        cwd = Path('.', open=io_open, joinpath=path_join, exists=path_exists)

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
