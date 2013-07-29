'''audit_usage -- get usage stats from I2B2 QT_ tables

.. todo:: mock data for testing

'''

from sqlalchemy import orm, MetaData
from sqlalchemy import Table, Column, ForeignKey
from sqlalchemy.types import Integer, String, DATETIME
from injector import inject

import i2b2pm


class I2B2Usage(object):
    @inject(datasrc=(orm.session.Session, i2b2pm.CONFIG_SECTION))
    def __init__(self, datasrc):
        self._datasrc = datasrc

    def q(self, sql):
        return self._datasrc().execute(sql).fetchall()


class I2B2AggregateUsage(I2B2Usage):
    def __repr__(self):
        return 'I2B2AggregateUsage()'

    def current_release(self):
        return self.q('''
            select project_name from I2B2PM.PM_PROJECT_DATA
            where project_id = 'BlueHeron' ''')[0].project_name

    def current_sessions(self):
        return self.q('''
select full_name, user_id, entry_date
from I2B2PM.pm_user_session
where user_id not like '%SERVICE_ACCOUNT'
and expired_date > sysdate
''')

    def total_number_of_queries(self):
        data = self.q('''
            select count(*) as total_number_of_queries
            from BLUEHERONDATA.qt_query_master qqm
            where qqm.name != 'HERON MONITORING QUERY'
        ''')
        if len(data) != 1:
            raise ValueError('expected 1 row; got: %s' % len(data))

        return data[0].total_number_of_queries

    def queries_by_month(self):
        return self.q('''
            select y, m, count(*) qty, count(distinct user_id) users
            from (
                select extract(year from qqm.create_date) y
                     , extract(month from qqm.create_date) m
                     , qqm.user_id
                from BLUEHERONDATA.qt_query_master qqm
                where qqm.name != 'HERON MONITORING QUERY'
            ) group by y, m
            order by y desc, m desc
                      ''')

    def query_volume(self, recent=False):
        '''overall query volume by user
        '''
        return self.q('''
select pud.full_name, all_time.user_id
     , two_weeks.qty two_weeks
     , last_month.qty last_month
     , last_quarter.qty last_quarter
     , last_year.qty last_year
     , all_time.qty all_time from
(select qqm.user_id, count(*) as qty
from BLUEHERONDATA.qt_query_master qqm
where qqm.name != 'HERON MONITORING QUERY'
group by qqm.user_id) all_time

left join

(select qqm.user_id, count(*) as qty
from BLUEHERONDATA.qt_query_master qqm
where qqm.create_date >= sysdate - 14
and qqm.name != 'HERON MONITORING QUERY'
group by qqm.user_id) two_weeks

on two_weeks.user_id = all_time.user_id

left join

(select qqm.user_id, count(*) as qty
from BLUEHERONDATA.qt_query_master qqm
where qqm.create_date >= sysdate - 30
and qqm.name != 'HERON MONITORING QUERY'
group by qqm.user_id) last_month

on last_month.user_id = all_time.user_id

left join

(select qqm.user_id, count(*) as qty
from BLUEHERONDATA.qt_query_master qqm
where qqm.create_date >= sysdate - 90
and qqm.name != 'HERON MONITORING QUERY'
group by qqm.user_id) last_quarter

on last_quarter.user_id = all_time.user_id

left join

(select qqm.user_id, count(*) as qty
from BLUEHERONDATA.qt_query_master qqm
where qqm.create_date >= sysdate - 365
and qqm.name != 'HERON MONITORING QUERY'
group by qqm.user_id) last_year

on last_year.user_id = all_time.user_id

        join i2b2pm.pm_user_data pud
          on all_time.user_id = pud.user_id

order by nvl(two_weeks.qty, -1) desc, nvl(all_time.qty, -1) desc
                      ''')

    def recent_query_performance(self):
        '''Show recent I2B2 queries.'''
        return self.q('''
select qm.query_master_id, qm.name, qm.user_id, qt.name as status,
  nvl(cast(qi.end_date as timestamp),
      -- round to nearest second by converting to date and back
      cast(cast(current_timestamp as date) as timestamp))
  - cast(qm.create_date as timestamp) elapsed,
  qm.create_date, qi.end_date, qi.batch_mode, qm.request_xml,
  rt.result_type_id, rt.description result_type_description
FROM (
  select * from (
   select * from blueherondata.qt_query_master qm
   where qm.delete_flag != 'Y'
   order by qm.query_master_id desc
   ) where rownum < 40) qm
JOIN blueherondata.qt_query_instance qi
ON qm.query_master_id = qi.query_master_id

left JOIN blueherondata.qt_query_result_instance qri
ON qi.query_instance_id = qri.query_instance_id

left JOIN blueherondata.qt_query_result_type rt
ON rt.result_type_id = qri.result_type_id
left JOIN blueherondata.qt_query_status_type qt
ON qt.status_type_id = qi.status_type_id

order by start_date desc
''')


class I2B2SensitiveUsage(I2B2Usage):
    def __repr__(self):
        return 'I2B2SensitiveUsage()'

    def patient_set_queries(self, recent=False, small=False):
        '''Queries that returned set sizes less than 10
        '''
        r = ('and qqm.create_date > sysdate - 45'
             if recent else '')
        s = ('and qqri.real_set_size <= 15 and qqri.set_size > 0'
             if small else '')

        return self.q('''
        select pud.full_name, qqm.user_id
             , qqm.query_master_id, qqm.name, qqm.create_date
             , qqri.set_size
        from BLUEHERONDATA.qt_query_master qqm
        join i2b2pm.pm_user_data pud
          on pud.user_id = qqm.user_id
        join BLUEHERONDATA.qt_query_instance qqi
          on qqm.query_master_id=qqi.query_master_id
        join BLUEHERONDATA.qt_query_result_instance qqri
          on qqi.query_instance_id=qqri.query_instance_id
        join BLUEHERONDATA.qt_query_result_type qqrt
          on qqri.result_type_id=qqrt.result_type_id
        where qqri.result_type_id=1
        %(RECENT)s %(SMALL)s
        order by substr(qqm.user_id, 2), create_date desc
        ''' % dict(RECENT=r, SMALL=s))

    def small_set_concepts(self):
        '''concepts used by users who ran query patient set which is less
        than 10.'''
        return self.q('''
        select user_id
             , qm.query_master_id
             , create_date
             , name as query_name
             , substr(extract(column_value, '/item/item_name/text()'), 1)
               as item_name
             , substr(extract(column_value, '/item/tooltip/text()'), 1)
               as tooltip
             , substr(extract(column_value, '/item/item_key/text()'), 1)
               as item_key
        from BLUEHERONDATA.QT_QUERY_MASTER qm
           , table(xmlsequence(extract(sys.XMLType(qm.request_xml),
                      '/qd:query_definition/panel[position()=last()
                      or position()=1]/item',
        'xmlns:qd="http://www.i2b2.org/xsd/cell/crc/psm/querydefinition/1.1/"')
                        ))
        where qm.query_master_id in  ( select qqm.query_master_id
                      from BLUEHERONDATA.qt_query_master qqm
                      join BLUEHERONDATA.qt_query_instance qqi
                        on qqm.query_master_id=qqi.query_master_id
                      join BLUEHERONDATA.qt_query_result_instance qqri
                        on qqi.query_instance_id=qqri.query_instance_id
                      join BLUEHERONDATA.qt_query_result_type qqrt
                        on qqri.result_type_id=qqrt.result_type_id
                      where qqri.real_set_size <= 15 and qqri.set_size > 0
                        and qqri.result_type_id=1
                        and qqm.create_date > sysdate - 45)
        order by create_date desc
        ''')

    def current_sessions(self):
        return self.q('''
select ud.full_name, ud.user_id, us.entry_date
from I2B2PM.pm_user_session us
join I2B2PM.pm_user_data ud on ud.user_id = us.user_id
where us.expired_date > sysdate
and us.user_id not like '%_SERVICE_ACCOUNT'
                      ''')

    def current_queries(self):
        return self.q('''
select ud.full_name, ud.user_id, us.entry_date
     , qm.query_master_id
     , qm.name, qm.create_date
     , qi.batch_mode
     , st.description status
     , qrt.description result_type

from I2B2PM.pm_user_session us
join I2B2PM.pm_user_data ud on ud.user_id = us.user_id

left join BlueHeronData.qt_query_master qm
  on ud.user_id = qm.user_id
 and qm.create_date > us.entry_date
left join BlueHeronData.qt_query_instance qi
  on qi.query_master_id = qm.query_master_id
left join BlueHeronData.qt_query_result_instance qri
  on qri.query_instance_id = qi.query_instance_id
left join BLUEHERONDATA.qt_query_status_type st
  on st.status_type_id = qi.status_type_id
left join BLUEHERONDATA.qt_query_result_type qrt
  on qrt.result_type_id = qri.result_type_id


where us.expired_date > sysdate
and us.user_id not like '%_SERVICE_ACCOUNT'

and (qm.query_master_id is null  or (
    qi.status_type_id = 5 -- INCOMPLETE
     and qm.delete_flag = 'N'
     and qi.end_date is null

     -- where qi.end_date is null
     -- and qri.end_date is null
     -- order by qm.create_date desc
))

order by ud.full_name, qm.create_date
                      ''')


# Hmm... messy...
# meta = i2b2pm.Base.metadata
meta = MetaData()
qm = Table('qt_query_master', meta,
           Column('query_master_id', Integer, primary_key=True),
           Column('user_id', String),
           Column('name', String),
           Column('request_xml', String),
           schema='blueherondata').alias('qm')

rt = Table('qt_query_result_type', meta,
           Column('result_type_id', Integer, primary_key=True),
           Column('name', String),  # result_type
           Column('description', String),
           schema='blueherondata').alias('rt')

qt = Table('qt_query_status_type', meta,
           Column('status_type_id', Integer, primary_key=True),
           Column('description', String),
           schema='blueherondata').alias('qt')

qi = Table('qt_query_instance', meta,
           Column('query_instance_id', Integer, primary_key=True),
           Column('query_master_id', Integer,
                  ForeignKey(qm.c.query_master_id)),
           Column('status_type_id', Integer,
                  ForeignKey(qt.c.status_type_id)),
           Column('start_date', DATETIME),
           Column('end_date', DATETIME),
           Column('message', String),
           schema='blueherondata').alias('qi')

qri = Table('qt_query_result_instance', meta,
            Column('query_instance_id', Integer,
                   ForeignKey(qi.c.query_instance_id)),
            Column('result_type_id', Integer,
                   ForeignKey(rt.c.result_type_id)),
            Column('set_size', Integer),
            schema='blueherondata').alias('qri')

s = Table('pm_user_session', meta,
          Column('session_id', String),
          Column('user_id', String),
          Column('entry_date', DATETIME),
          Column('expired_date', DATETIME),
          schema='i2b2pm').alias('s')


def _integration_test():  # pragma: nocover
    import logging
    import pprint

    log = logging.getLogger(__name__)

    logging.basicConfig(level=logging.DEBUG)

    (agg, detail) = i2b2pm.RunTime.make(None,
                                        [I2B2AggregateUsage,
                                         I2B2SensitiveUsage])

    log.info('Total queries: %s',
             pprint.pformat(agg.total_number_of_queries()))
    log.info('Queries by month: %s',
             pprint.pformat(agg.queries_by_month()))
    log.info('Query volume by user: %s',
             pprint.pformat(agg.query_volume()))
    log.info('Recent small patient set queries: %s',
             pprint.pformat(detail.patient_set_queries(recent=True,
                                                       small=True)))
    log.info('Concepts for recent small patient set queries: %s',
             pprint.pformat(detail.small_set_concepts()))
    log.info('Current sessions: %s', pprint.pformat(detail.current_sessions()))
    log.info('Current queries: %s', pprint.pformat(detail.current_queries()))


def _report_with_roles(argv, stdout):  # pragma: nocover
    import csv

    import i2b2pm
    import medcenter

    (usage, ) = i2b2pm.RunTime.make(None, [I2B2AggregateUsage])
    data = usage.query_volume()

    (mc, ) = medcenter.RunTime.make(None, [medcenter.MedCenter])

    out = csv.writer(stdout)
    cols = ('Faculty', 'Title', 'Department', 'Name', 'ID',
            'Weeks2', 'Month', 'Quarter', 'Year', 'All')
    out.writerow(cols)

    for row in data:
        cn = row[1]
        try:
            agent = mc.lookup(cn)
            fac, title, dept = mc.is_faculty(agent), agent.title, agent.ou
        except KeyError:
            fac, title, dept = None, None, None
        out.writerow((fac, title, dept) + tuple(row))


if __name__ == '__main__':

    _integration_test()
    #a, s = _hide_sys()
    #_report_with_roles(a, s)
