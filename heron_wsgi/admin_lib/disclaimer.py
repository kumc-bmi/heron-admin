'''
  >>> from sqlalchemy import create_engine
  >>> e = create_engine('sqlite://')
'''

import StringIO

# from pypi
from lxml import etree
import urllib2
import sqlalchemy
from sqlalchemy import Table, Column, text
from sqlalchemy.types import INTEGER, VARCHAR, TEXT, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import mapper, column_property
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


class Disclaimer(object):
    def __str__(self):
        return 'Disclaimer%s' % (
            (self.disclaimer_id, self.url, self.current),)

    def content(self, ua):
        r'''
           >>> d = Disclaimer()
           >>> d.url = 'http://example/'
           >>> d.content(_TestUrlOpener())
           '<div id="blog-main">\nmain blog copy...\n</div>\n...\n'
        '''
        body = ua.open(self.url).read()
        kludge = StringIO.StringIO(body.replace('&larr;', ''
                                                ).replace('&rarr;', '')
                                   )  #KLUDGE
        elt = etree.parse(kludge).xpath('//*[@id="blog-main"]')[0]
        return etree.tostring(elt)

_test_doc='''
<!DOCTYPE html>
<html><head><title>...</title></head>
<body>
...
<div id='blog-main'>
main blog copy...
</div>
...
</body>
</html>
'''

class _TestUrlOpener(object):
    def open(self, addr):
        return StringIO.StringIO(_test_doc)


def make_map():
    fields = ('disclaimer_id', 'url', 'current')

    cols, j, w = eav_join(redcap_data.select().where(
            redcap_data.c.project_id==35).alias('disclaimers'),  #@@
                       ('project_id', 'record'),
                       fields,
                       'field_name', 'value')

    mapper(Disclaimer, select(cols).where(w).apply_labels().alias(),
           primary_key=[cols[0]],
           properties=dict(dict(zip(fields, cols))))


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
    s = sm()
    for d in s.query(Disclaimer).filter(Disclaimer.current==1):
        print d
        print d.content(urllib2.build_opener())
