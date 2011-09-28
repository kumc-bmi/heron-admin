'''
  >>> from sqlalchemy import create_engine
  >>> e = create_engine('sqlite://')
'''

# from pypi
import sqlalchemy
from sqlalchemy import Table, Column, text
from sqlalchemy.types import INTEGER, VARCHAR, TEXT, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import mapper
from sqlalchemy.sql import join, and_, select
from sqlalchemy.orm import sessionmaker

import config
from db_util import mysql_connect
from heron_policy import REDCAPDB_CONFIG_SECTION

Base = declarative_base()
metadata = Base.metadata

redcap_data = Table('redcap_data', metadata,
                    Column(u'project_id', INTEGER(),
                           nullable=False, default=text(u"'0'"),
                           primary_key=True),
                    Column(u'event_id', INTEGER(), primary_key=True),
                    Column(u'record', VARCHAR(length=100), primary_key=True),
                    Column(u'field_name', VARCHAR(length=100),
                           primary_key=True),
                    Column(u'value', TEXT()),
                    )

def eachcol(t1, t2, cols):
    '''
      >>> pairs = eachcol(redcap_data, redcap_data,
      ...                 ['project_id', 'record'])
      >>> pairs[0][0].name
      u'project_id'
    '''
    # .columns is an OrderedDict, so we can correlate indexes.
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
      >>> m, j0 = eav_join(redcap_data,
      ...                  ['project_id', 'record'],
      ...                  ['url'],
      ...                  'field_name', 'value')
      >>> print j0.select()
      SELECT project_id, event_id, record, field_name, value 
      FROM (SELECT redcap_data.project_id AS project_id, redcap_data.event_id AS event_id, redcap_data.record AS record, redcap_data.field_name AS field_name, redcap_data.value AS value 
      FROM redcap_data 
      WHERE redcap_data.field_name = :field_name_1)

      >>> m
      [Column(u'value', TEXT(), table=<redcap_data>)]

      >>> m1, j1 = eav_join(redcap_data,
      ...                  ['project_id', 'record'],
      ...                  ['url', 'name'],
      ...                  'field_name', 'value')
      >>> print select(m1)
      SELECT redcap_data.value, j_name.value 
      FROM redcap_data, (SELECT project_id AS project_id, event_id AS event_id, record AS record, field_name AS field_name, value AS value, redcap_data.project_id AS redcap_data_project_id, redcap_data.event_id AS redcap_data_event_id, redcap_data.record AS redcap_data_record, redcap_data.field_name AS redcap_data_field_name, redcap_data.value AS redcap_data_value 
      FROM (SELECT redcap_data.project_id AS project_id, redcap_data.event_id AS event_id, redcap_data.record AS record, redcap_data.field_name AS field_name, redcap_data.value AS value 
      FROM redcap_data 
      WHERE redcap_data.field_name = :field_name_1) JOIN redcap_data ON project_id = redcap_data.project_id AND record = redcap_data.record AND redcap_data.field_name = :field_name_2) AS j_name

      >>> m2, j2 = eav_join(redcap_data,
      ...                  ['project_id', 'record'],
      ...                  ['url', 'name', 'current'],
      ...                  'field_name', 'value')
      >>> print select(m2)
      SELECT redcap_data.value, j_name.value, j_current.j_name_value 
      FROM redcap_data, (SELECT project_id AS project_id, event_id AS event_id, record AS record, field_name AS field_name, value AS value, redcap_data.project_id AS redcap_data_project_id, redcap_data.event_id AS redcap_data_event_id, redcap_data.record AS redcap_data_record, redcap_data.field_name AS redcap_data_field_name, redcap_data.value AS redcap_data_value 
      FROM (SELECT redcap_data.project_id AS project_id, redcap_data.event_id AS event_id, redcap_data.record AS record, redcap_data.field_name AS field_name, redcap_data.value AS value 
      FROM redcap_data 
      WHERE redcap_data.field_name = :field_name_1) JOIN redcap_data ON project_id = redcap_data.project_id AND record = redcap_data.record AND redcap_data.field_name = :field_name_2) AS j_name, (SELECT j_name.project_id AS j_name_project_id, j_name.event_id AS j_name_event_id, j_name.record AS j_name_record, j_name.field_name AS j_name_field_name, j_name.value AS j_name_value, j_name.redcap_data_project_id AS j_name_redcap_data_project_id, j_name.redcap_data_event_id AS j_name_redcap_data_event_id, j_name.redcap_data_record AS j_name_redcap_data_record, j_name.redcap_data_field_name AS j_name_redcap_data_field_name, j_name.redcap_data_value AS j_name_redcap_data_value, redcap_data.project_id AS redcap_data_project_id, redcap_data.event_id AS redcap_data_event_id, redcap_data.record AS redcap_data_record, redcap_data.field_name AS redcap_data_field_name, redcap_data.value AS redcap_data_value 
      FROM (SELECT project_id AS project_id, event_id AS event_id, record AS record, field_name AS field_name, value AS value, redcap_data.project_id AS redcap_data_project_id, redcap_data.event_id AS redcap_data_event_id, redcap_data.record AS redcap_data_record, redcap_data.field_name AS redcap_data_field_name, redcap_data.value AS redcap_data_value 
      FROM (SELECT redcap_data.project_id AS project_id, redcap_data.event_id AS event_id, redcap_data.record AS record, redcap_data.field_name AS field_name, redcap_data.value AS value 
      FROM redcap_data 
      WHERE redcap_data.field_name = :field_name_1) JOIN redcap_data ON project_id = redcap_data.project_id AND record = redcap_data.record AND redcap_data.field_name = :field_name_2) AS j_name JOIN redcap_data ON j_name.project_id = redcap_data.project_id AND j_name.record = redcap_data.record AND redcap_data.field_name = :field_name_3) AS j_current
    '''

    #aliases = dict([(n, t.alias('t_' + n)) for n in attrs])

    # use itertools rather than for loop for fold?
    #a0 = aliases[attrs[0]]
    product = t.select().where(t.columns[acol] == attrs[0])
    vcols = [t.columns[vcol]]
    vcolnum = t.columns.keys().index(vcol)

    for n in attrs[1:]:
        where = and_(colsmatch(product, t, keycols), (t.columns[acol] == n))
        product = product.join(t, where).alias('j_' + n)
        vcols.append(product.columns[product.columns.keys()[vcolnum]])

    return vcols, product


class Disclaimer(object):
    pass


def make_map():
    fields = ('disclaimer_id', 'name', 'url', 'current')

    cols, j = eav_join(redcap_data,
                       ('project_id', 'record'),
                       fields,
                       'field_name', 'value')

    mapper(Disclaimer, select(cols),
           properties=dict(dict(zip(fields, cols)),
                           project_id=j.c.project_id,
                           record=j.c.record))


def rt_engine(ini, section=REDCAPDB_CONFIG_SECTION, driver='mysql+mysqldb'):
    rt = config.RuntimeOptions('user password host sid engine'.split())
    rt.load(ini, section)
    u = sqlalchemy.engine.url.URL(driver, rt.user, rt.password,
                                  rt.host, 3306, 'redcap')
    return sqlalchemy.create_engine(u)

def datasource(ini, section=REDCAPDB_CONFIG_SECTION, driver='mysql+mysqldb'):
    '''
    .. todo: refactor into datasource
    '''
    e = rt_engine(ini, section, driver)
    def get_connection():
        #return oracle_connect(rt.user, rt.password, rt.host, 1521, rt.sid)
        #return mysql_connect(rt.user, rt.password, rt.host, 3306, 'redcap')
        return e.connect()
    return get_connection


if __name__ == '__main__':
    make_map()
    ds = datasource('integration-test.ini')

    conn = ds()
    #cur = conn.cursor()
    r = conn.execute(redcap_data.select(redcap_data.c.project_id==35))
    print r.fetchall()


    engine = rt_engine('integration-test.ini')
    Base.metadata.bind = engine
    sm = sessionmaker(engine)
    print sm
    s = sm()
    print s
    print s.query(Disclaimer).all()
