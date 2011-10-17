'''redcapdb -- a little ORM support for REDCap's EAV structure
'''

import injector
from injector import inject, provides
import sqlalchemy
from sqlalchemy import Table, Column, text
from sqlalchemy.types import INTEGER, VARCHAR, TEXT, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import mapper, column_property
from sqlalchemy.sql import join, and_, select

import config

CONFIG_SECTION='redcapdb'

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
      >>> cols1, j1, w1 = eav_join(redcap_data,
      ...                          ['project_id', 'record'],
      ...                          ['url'],
      ...                          'field_name', 'value')
      >>> cols1
      [Column(u'value', TEXT(), table=<j_url>)]

      >>> print select(cols1).where(w1)
      SELECT j_url.value 
      FROM redcap_data AS j_url 
      WHERE j_url.field_name = :field_name_1

      >>> c2, j2, w2 = eav_join(redcap_data,
      ...                       ['project_id', 'record'],
      ...                       ['url', 'name'],
      ...                       'field_name', 'value')
      >>> print select(c2).where(w2)
      SELECT j_url.value, j_name.value 
      FROM redcap_data AS j_url, redcap_data AS j_name 
      WHERE j_url.field_name = :field_name_1 AND j_url.project_id = j_name.project_id AND j_url.record = j_name.record AND j_name.field_name = :field_name_2


      >>> c3, j3, w3 = eav_join(redcap_data,
      ...                       ['project_id', 'record'],
      ...                       ['disclaimer_id', 'url', 'current'],
      ...                       'field_name', 'value')
      >>> print select(c3).where(w3).apply_labels()
      SELECT j_disclaimer_id.value AS j_disclaimer_id_value, j_url.value AS j_url_value, j_current.value AS j_current_value 
      FROM redcap_data AS j_disclaimer_id, redcap_data AS j_url, redcap_data AS j_current 
      WHERE j_disclaimer_id.field_name = :field_name_1 AND j_disclaimer_id.project_id = j_url.project_id AND j_disclaimer_id.record = j_url.record AND j_url.field_name = :field_name_2 AND j_disclaimer_id.project_id = j_current.project_id AND j_disclaimer_id.record = j_current.record AND j_current.field_name = :field_name_3
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


def redcap_eav_map(pid, cls, fields, alias='eav'):
    '''
    @param pid: redcap project id to select
    @param cls: class to map
    @param fields: 1st is primary key
    '''
    data = redcap_data.select().where(redcap_data.c.project_id==pid)
    cols, j, w = eav_join(data.alias(alias),
                          keycols=('project_id', 'record'),
                          attrs=fields,
                          acol='field_name', vcol='value')

    mapper(cls, select(cols).where(w).apply_labels().alias(),
           primary_key=[cols[0]],
           properties=dict(zip(fields, cols)))

    return cols, w


class RunTime(injector.Module):
    def __init__(self, ini):
        self._ini = ini

    def configure(self, binder):
        def bind_options(names, section):
            rt = config.RuntimeOptions(names)
            rt.load(self._ini, section)
            binder.bind((config.Options, section), rt)

        #@@todo: rename sid to database (check sqlalchemy docs 1st)
        bind_options('user password host port database engine'.split(), CONFIG_SECTION)

    @provides((sqlalchemy.engine.base.Connectable, CONFIG_SECTION))
    @inject(rt=(config.Options, CONFIG_SECTION))
    def redcap_datasource(self, rt, driver='mysql+mysqldb'):
        # support sqlite3 driver?
        u = (rt.engine if rt.engine else
             sqlalchemy.engine.url.URL(driver, rt.user, rt.password,
                                       rt.host, rt.port, rt.database))

        # inverted w.r.t. object capability style, no?
        return sqlalchemy.create_engine(u)

    @classmethod
    def mods(cls, ini):
        return [cls(ini)]
