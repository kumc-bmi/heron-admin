'''audit_usage -- get usage stats from I2B2 QT_ tables

.. todo:: mock data for testing

'''


from sqlalchemy import orm

from injector import inject

import i2b2pm


class I2B2Usage(object):
    @inject(datasrc=(orm.session.Session, i2b2pm.CONFIG_SECTION),
            i2b2crc_schema=i2b2pm.Ki2b2crc_schema,
            i2b2pm_schema=i2b2pm.Ki2b2pm_schema)
    def __init__(self, datasrc, i2b2crc_schema, i2b2pm_schema):
        self._datasrc = datasrc
        self.schemas = dict(pm=i2b2pm_schema, crc=i2b2crc_schema)

    def q(self, sql):
        return self._datasrc().execute(sql).fetchall()


class I2B2AggregateUsage(I2B2Usage):
    def __repr__(self):
        return 'I2B2AggregateUsage()'

    def current_release(self):
        return self.q('''
            select project_name from %(pm)s.PM_PROJECT_DATA
            where project_id = 'BlueHeron' ''' %
                     self.schemas)[0].project_name

    def current_sessions(self):
        return self.q('''
select pud.full_name, s.user_id, s.entry_date
from %(pm)s.pm_user_session s
join %(pm)s.pm_user_data pud
  on s.user_id = pud.user_id
where s.user_id not like '%%SERVICE_ACCOUNT'
and s.expired_date > current_date
''' % self.schemas)

    def total_number_of_queries(self):
        data = self.q('''
            select count(*) as total_number_of_queries
            from %(crc)s.qt_query_master qqm
            where qqm.name != 'HERON MONITORING QUERY'
        ''' % self.schemas)
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
                from %(crc)s.qt_query_master qqm
                where qqm.name != 'HERON MONITORING QUERY'
            ) t  group by y, m
            order by y desc, m desc
                      ''' % self.schemas)

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
from %(crc)s.qt_query_master qqm
where qqm.name != 'HERON MONITORING QUERY'
group by qqm.user_id) all_time

left join

(select qqm.user_id, count(*) as qty
from %(crc)s.qt_query_master qqm
where qqm.create_date >= current_date - 14
and qqm.name != 'HERON MONITORING QUERY'
group by qqm.user_id) two_weeks

on two_weeks.user_id = all_time.user_id

left join

(select qqm.user_id, count(*) as qty
from %(crc)s.qt_query_master qqm
where qqm.create_date >= current_date - 30
and qqm.name != 'HERON MONITORING QUERY'
group by qqm.user_id) last_month

on last_month.user_id = all_time.user_id

left join

(select qqm.user_id, count(*) as qty
from %(crc)s.qt_query_master qqm
where qqm.create_date >= current_date - 90
and qqm.name != 'HERON MONITORING QUERY'
group by qqm.user_id) last_quarter

on last_quarter.user_id = all_time.user_id

left join

(select qqm.user_id, count(*) as qty
from %(crc)s.qt_query_master qqm
where qqm.create_date >= current_date - 365
and qqm.name != 'HERON MONITORING QUERY'
group by qqm.user_id) last_year

on last_year.user_id = all_time.user_id

        join %(pm)s.pm_user_data pud
          on all_time.user_id = pud.user_id

order by coalesce(two_weeks.qty, -1) desc, coalesce(all_time.qty, -1) desc
                      ''' % self.schemas)

    def recent_query_performance(self):
        '''Show recent I2B2 queries.

        .. note: Query status for Timeline Queries has been changed to
                 COMPLETED as per the show_performance() in
                 perf_reports.py
        '''
        return self.q('''
select * from(
  select * from (
  select qm.query_master_id, qm.name, qm.user_id, qt.name as status,
  coalesce(cast(qi.end_date as timestamp),
      -- round to nearest second by converting to date and back
      cast(cast(current_timestamp as date) as timestamp))
  - cast(qm.create_date as timestamp) elapsed,
  qm.create_date,
  qi.end_date,
  qi.batch_mode,
  qm.request_xml  ,
  rt.result_type_id,
  rt.description result_type_description
FROM (
  select * from (
   select * from %(crc)s.qt_query_master qm
   where qm.delete_flag != 'Y' order by qm.create_date desc
   ) t ) qm
JOIN %(crc)s.qt_query_instance qi
ON qm.query_master_id = qi.query_master_id

left JOIN %(crc)s.qt_query_result_instance qri
ON qi.query_instance_id = qri.query_instance_id

left JOIN %(crc)s.qt_query_result_type rt
ON rt.result_type_id = qri.result_type_id
left JOIN %(crc)s.qt_query_status_type qt
ON qt.status_type_id = qi.status_type_id
where qm.create_date>current_date-14

UNION ALL

select
 qm.query_master_id
,(select qri.description from %(crc)s.qt_query_result_instance qri
 where qri.result_instance_id=
 cast(regexp_replace(
substr(qm.request_xml,
abs(STRPOS(qm.request_xml,'<patient_set_coll_id>') +21
-STRPOS(qm.request_xml,'</patient_set_coll_id>'))
,STRPOS(qm.request_xml,'<patient_set_coll_id>')+21
)
, '[^0-9]+', '') as numeric))  as name
,qm.user_id
,'COMPLETED' as status
,cast(cast(qm.create_date as date) as timestamp)
  - cast(qm.create_date as timestamp)   elapsed
,qm.create_date
,qm.create_date as end_date
,'' as batch_mode
,qm.request_xml
,9 as result_type_id
,'Timeline' as result_type_description

 from %(crc)s.qt_pdo_query_master qm
join %(pm)s.pm_user_data ud on qm.user_id=ud.user_id
where qm.create_date>current_date-14
) rqp order by rqp.create_date desc)rqp

order by rqp.create_date desc
limit 40
''' % self.schemas)


class I2B2SensitiveUsage(I2B2Usage):
    def __repr__(self):
        return 'I2B2SensitiveUsage()'

    def patient_set_queries(self, recent=False, small=False):
        '''Queries that returned set sizes less than 10
        '''
        r = ('and qqm.create_date > current_date - 45'
             if recent else '')
        s = ('and qqri.real_set_size <= 15 and qqri.set_size > 0'
             if small else '')

        return self.q('''
        select pud.full_name, qqm.user_id
             , qqm.query_master_id, qqm.name, qqm.create_date
             , qqri.set_size
        from %(crc)s.qt_query_master qqm
        join %(pm)s.pm_user_data pud
          on pud.user_id = qqm.user_id
        join %(crc)s.qt_query_instance qqi
          on qqm.query_master_id=qqi.query_master_id
        join %(crc)s.qt_query_result_instance qqri
          on qqi.query_instance_id=qqri.query_instance_id
        join %(crc)s.qt_query_result_type qqrt
          on qqri.result_type_id=qqrt.result_type_id
        where qqri.result_type_id=1
        %(RECENT)s %(SMALL)s
        order by substr(qqm.user_id, 2), create_date desc
        ''' % dict(RECENT=r, SMALL=s, crc=self.schemas['crc']), 
                  pm=self.schemas['pm']))

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
        from %(crc)s.QT_QUERY_MASTER qm
           , table(xmlsequence(extract(sys.XMLType(qm.request_xml),
                      '/qd:query_definition/panel[position()=last()
                      or position()=1]/item',
        'xmlns:qd="http://www.i2b2.org/xsd/cell/crc/psm/querydefinition/1.1/"')
                        ))
        where qm.query_master_id in  ( select qqm.query_master_id
                      from %(crc)s.qt_query_master qqm
                      join %(crc)s.qt_query_instance qqi
                        on qqm.query_master_id=qqi.query_master_id
                      join %(crc)s.qt_query_result_instance qqri
                        on qqi.query_instance_id=qqri.query_instance_id
                      join %(crc)s.qt_query_result_type qqrt
                        on qqri.result_type_id=qqrt.result_type_id
                      where qqri.real_set_size <= 15 and qqri.set_size > 0
                        and qqri.result_type_id=1
                        and qqm.create_date > current_date - 45)
        order by create_date desc
        ''' % self.schemas)

    def current_sessions(self):
        return self.q('''
select ud.full_name, ud.user_id, us.entry_date
from %(pm)s.pm_user_session us
join %(pm)s.pm_user_data ud on ud.user_id = us.user_id
where us.expired_date > current_date
and us.user_id not like '%%_SERVICE_ACCOUNT'
                      ''' % self.schemas)

    def current_queries(self):
        return self.q('''
select ud.full_name, ud.user_id, us.entry_date
     , qm.query_master_id
     , qm.name, qm.create_date
     , qi.batch_mode
     , st.description status
     , qrt.description result_type

from %(pm)s.pm_user_session us
join %(pm)s.pm_user_data ud on ud.user_id = us.user_id

left join %(crc)s.qt_query_master qm
  on ud.user_id = qm.user_id
 and qm.create_date > us.entry_date
left join %(crc)s.qt_query_instance qi
  on qi.query_master_id = qm.query_master_id
left join %(crc)s.qt_query_result_instance qri
  on qri.query_instance_id = qi.query_instance_id
left join %(crc)s.qt_query_status_type st
  on st.status_type_id = qi.status_type_id
left join %(crc)s.qt_query_result_type qrt
  on qrt.result_type_id = qri.result_type_id


where us.expired_date > current_date
and us.user_id not like '%%_SERVICE_ACCOUNT'

and (qm.query_master_id is null  or (
    qi.status_type_id = 5 -- INCOMPLETE
     and qm.delete_flag = 'N'
     and qi.end_date is null

     -- where qi.end_date is null
     -- and qri.end_date is null
     -- order by qm.create_date desc
))

order by ud.full_name, qm.create_date
                      ''' % self.schemas)


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
    log.info('Recent queries: %s',
             pprint.pformat(agg.recent_query_performance()))


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
