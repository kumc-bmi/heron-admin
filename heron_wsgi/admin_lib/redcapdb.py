'''redcapdb -- a little ORM support for REDCap's EAV structure
--------------------------------------------------------------

'''

import logging

import injector
from injector import inject, provides, singleton
import sqlalchemy
from sqlalchemy import Table, Column, text
from sqlalchemy.types import INTEGER, VARCHAR, TEXT, DATETIME
from sqlalchemy.orm import mapper
from sqlalchemy.sql import and_, select
from sqlalchemy.ext.declarative import declarative_base

import rtconfig

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

          >>> (smaker, ) = Mock.make([(sqlalchemy.orm.session.Session,
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

      >>> (smaker, ) = Mock.make([(sqlalchemy.orm.session.Session,
      ...                          CONFIG_SECTION)])
      >>> s = smaker()
      >>> for k, v in (('study_id', 'test_002'), ('age', 32)):
      ...     s.execute(redcap_data.insert().values(event_id=321,
      ...                                           project_id=123,
      ...                                           record=1,
      ...                                           field_name=k,
      ...                                           value=v)) and None

      >>> list(allfields(s, 123, 1))
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
    @provides((sqlalchemy.orm.session.Session, CONFIG_SECTION))
    @inject(engine=(sqlalchemy.engine.base.Connectable, CONFIG_SECTION))
    def redcap_sessionmaker(self, engine):
        return sqlalchemy.orm.sessionmaker(engine)


class Mock(injector.Module, rtconfig.MockMixin):
    @singleton
    @provides((sqlalchemy.engine.base.Connectable, CONFIG_SECTION))
    def redcap_datasource(self):
        import logging  # @@ lazy
        log = logging.getLogger(__name__)
        #salog = logging.getLogger('sqlalchemy.engine.base.Engine')
        #salog.setLevel(logging.INFO)
        log.debug('redcap create_engine: again?')
        e = sqlalchemy.create_engine('sqlite://')
        redcap_data.create(e)
        redcap_user_rights.create(e)
        return e

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
    def configure(self, binder):
        #@@todo: rename sid to database (check sqlalchemy docs 1st)
        self.bind_options(binder,
                          'user password host port database engine'.split(),
                          CONFIG_SECTION)

    @singleton
    @provides((sqlalchemy.engine.base.Connectable, CONFIG_SECTION))
    @inject(rt=(rtconfig.Options, CONFIG_SECTION))
    def redcap_datasource(self, rt, driver='mysql+mysqldb'):
        # support sqlite3 driver?
        u = (rt.engine if rt.engine else
             sqlalchemy.engine.url.URL(driver, rt.user, rt.password,
                                       rt.host, rt.port, rt.database))

        # http://www.sqlalchemy.org/docs/dialects/mysql.html
        #      #connection-timeouts
        return sqlalchemy.create_engine(u, pool_recycle=3600)

    @classmethod
    def mods(cls, ini):
        return [cls(ini), SetUp()]


def _integration_test():  # pragma: nocover
    '''Print distinct field_name from a given project_id.
    '''
    import sys
    from pprint import pprint

    project_id = int(sys.argv[-1])

    (sm, ) = RunTime.make(None, [(sqlalchemy.orm.session.Session,
                                 CONFIG_SECTION)])
    s = sm()
    print "slice of redcap_data:"
    pprint(s.query(redcap_data).slice(1, 10))
    pprint(s.query(redcap_data).slice(1, 10).all())

    print "field_name list:"
    ans = s.execute(select([redcap_data.c.field_name], distinct=True).\
                    where(redcap_data.c.project_id == project_id))
    pprint(ans.fetchall())

    print "users:"
    ans = s.execute(select([redcap_user_rights.c.username], distinct=True).\
                    where(redcap_user_rights.c.project_id == project_id))
    pprint(ans.fetchall())


if __name__ == '__main__':  # pragma: nocover
    _integration_test()
