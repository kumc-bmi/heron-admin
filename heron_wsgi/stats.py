'''stats -- HERON usage statistics

'''

import logging
import itertools
import operator

from injector import inject
from sqlalchemy import orm, func, between, case
from sqlalchemy import select, Table, Column, ForeignKey
from sqlalchemy.types import Integer, String, DATETIME
import datetime
import decimal

from admin_lib import heron_policy
from admin_lib import i2b2pm

log = logging.getLogger(__name__)


class UsageReports(object):
    @inject(datasrc=(orm.session.Session, i2b2pm.CONFIG_SECTION))
    def __init__(self, datasrc):
        self._datasrc = datasrc

    def q(self, sql):
        return self._datasrc().execute(sql).fetchall()

    def total_number_of_queries(self):
        data = self.q('''
            select count(*) as total_number_of_queries
            from BLUEHERONDATA.qt_query_master
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
group by qqm.user_id) all_time

left join

(select qqm.user_id, count(*) as qty
from BLUEHERONDATA.qt_query_master qqm
where qqm.create_date >= sysdate - 14
group by qqm.user_id) two_weeks

on two_weeks.user_id = all_time.user_id

left join

(select qqm.user_id, count(*) as qty
from BLUEHERONDATA.qt_query_master qqm
where qqm.create_date >= sysdate - 30
group by qqm.user_id) last_month

on last_month.user_id = all_time.user_id

left join

(select qqm.user_id, count(*) as qty
from BLUEHERONDATA.qt_query_master qqm
where qqm.create_date >= sysdate - 90
group by qqm.user_id) last_quarter

on last_quarter.user_id = all_time.user_id

left join

(select qqm.user_id, count(*) as qty
from BLUEHERONDATA.qt_query_master qqm
where qqm.create_date >= sysdate - 365
group by qqm.user_id) last_year

on last_year.user_id = all_time.user_id

        join i2b2pm.pm_user_data pud
          on all_time.user_id = pud.user_id

order by nvl(two_weeks.qty, -1) desc, nvl(all_time.qty, -1) desc
                      ''')

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

    def configure(self, config, mount_point):
        '''Connect this view to the rest of the application

        :param config: a pyramid config thingy@@@

        .. todo:: consider requiring DROC permissions on show_usage_report
        '''
        config.add_route('usage', mount_point + 'usage')
        config.add_view(self.show_usage_report, route_name='usage',
                        request_method='GET', renderer='report1.html',
                        permission=heron_policy.PERM_USER)
        config.add_route('usage_risky', mount_point + 'usage_risky')
        config.add_view(self.show_small_set_report, route_name='usage_risky',
                        request_method='GET', renderer='report2.html',
                        permission=heron_policy.PERM_USER)

    def show_usage_report(self, res, req):
        return dict(total_number_of_queries=self.total_number_of_queries(),
                    query_volume=self.query_volume(),
                    queries_by_month=self.queries_by_month(),
                    cycle=itertools.cycle)

    def show_small_set_report(self, res, req):
        return dict(
            summary=self.patient_set_queries(recent=True, small=True),
            detail=itertools.groupby(self.small_set_concepts(),
                                     operator.itemgetter('query_master_id')),
            cycle=itertools.cycle)


class Machine(object):
    '''Machine Interface

    .. todo:: clean up Machine dead code.

    See :class:`heron_wsgi.powerbox.LinuxMachine` for implementation.
    '''
    def load(self):
        '''Report load average(s) on the machine

        :returntype: list of (minutes, load) tuples.
        '''
        return [(1, 0.00), (5, 0.00), (15, 0.00)]


meta = i2b2pm.Base.metadata
qm = Table('qt_query_master', meta,
           Column('query_master_id', Integer, primary_key=True),
           Column('user_id', String),
           Column('name', String),
           Column('request_xml', String),
           schema='blueherondata')

rt = Table('qt_query_result_type', meta,
           Column('result_type_id', Integer, primary_key=True),
           Column('name', String),  # result_type
           Column('description', String),
           schema='blueherondata')

qt = Table('qt_query_status_type', meta,
           Column('status_type_id', Integer, primary_key=True),
           Column('description', String),
           schema='blueherondata')

qi = Table('qt_query_instance', meta,
           Column('query_instance_id', Integer, primary_key=True),
           Column('query_master_id', Integer,
                  ForeignKey(qm.c.query_master_id)),
           Column('status_type_id', Integer,
                  ForeignKey(qt.c.status_type_id)),
           Column('start_date', DATETIME),
           Column('end_date', DATETIME),
           Column('message', String),
           schema='blueherondata')

qri = Table('qt_query_result_instance', meta,
            Column('query_instance_id', Integer,
                   ForeignKey(qi.c.query_instance_id)),
            Column('result_type_id', Integer,
                   ForeignKey(rt.c.result_type_id)),
            Column('set_size', Integer),
            schema='blueherondata')

s = Table('pm_user_session', meta,
          Column('session_id', String),
          Column('user_id', String),
          Column('entry_date', DATETIME),
          Column('expired_date', DATETIME),
          schema='i2b2pm')


class PerformanceReports(UsageReports):
    @inject(datasrc=(orm.session.Session, i2b2pm.CONFIG_SECTION))
    def __init__(self, datasrc, cal=datetime.date.today):
        UsageReports.__init__(self, datasrc=datasrc)
        self._datasrc = datasrc
        self._cal = cal

    def configure(self, config, mount_point):
        '''Connect this view to the rest of the application

        :param config: a pyramid config thingy@@@

        .. todo:: consider allowing anonymous access to performance report.
        '''
        UsageReports.configure(self, config, mount_point)

        config.add_route('performance', mount_point + 'performance')
        config.add_view(self.show_performance, route_name='performance',
                        request_method='GET', renderer='performance.html',
                        permission=heron_policy.PERM_USER)

        config.add_route('performance_data', mount_point + 'performance_data')
        config.add_view(self.performance_data, route_name='performance_data',
                        request_method='GET', renderer='json',
                        permission=heron_policy.PERM_USER)

        config.add_route('query_data', mount_point + 'query_data')
        config.add_view(self.query_data, route_name='query_data',
                        request_method='GET', renderer='json',
                        permission=heron_policy.PERM_USER)

    def show_performance(self, res, req):
        return {}

    @classmethod
    def query_data_select(cls, statuses):
        log_or_null = case([(qi.c.end_date == None, None)],
                           else_=func.log(2, (qi.c.end_date - qi.c.start_date) * 24 * 60 * 60))

        stmt = select([qm.c.query_master_id, qm.c.user_id, qm.c.name.label('query_name'),
                       rt.c.name.label('result_type'),
                       rt.c.description.label('result_type_description'),
                       qri.c.set_size,
                       qi.c.start_date,
                       qt.c.description.label('status'),
                       qi.c.message,
                       qi.c.end_date,
                       log_or_null.label('value'),
                       qm.c.request_xml],
                      from_obj=[qm.join(qi).join(qri).join(rt).join(qt)])
        if statuses:
            stmt = stmt.where(qt.c.description.in_(statuses))
        return stmt

    def query_data(self, res, req):
        '''
        .. todo:: vary by date, ...
        '''
        log.debug('query_data about to get a session')
        session = self._datasrc()
        log.debug('query_data got a session: %s', session)

        weeks = 1
        thru = self._cal()
        date = thru + datetime.timedelta(-7 * weeks)
#        result_types = None  # all. or: ('PATIENT_COUNT_XML', 'PATIENTSET')

        qt = session.execute(self.query_data_select(req.GET.getall('status')).\
                                where(between(qi.c.start_date, date, thru)).\
                                order_by(qi.c.start_date))
###
#        where qi.start_date between :thru - :days and :thru
#        %(status_constraint)s
#        and qt.description in (%(status_enum)s)
#        and rt.name in (:result_type_enum)
#        order by qi.start_date;
#        ''' % dict(
#            # perhaps I should let SQLAlchemy do this...
#            status_constraint='and qt.description in (' + ', '.join(statuses) + ') '
#            if statuses else '',
#            result_type_constraint='and rt.name in (' + ', '.join(result_types) + ') '
#            if result_types else ''
#        ),

        model = dict(queries=to_json(qt))

        return model

    def performance_data(self, res, req):
        session = self._datasrc()
        this_month = session.execute('''
select * from (
select trunc(qi.start_date) start_day
     , qt.status_type_id, qi.batch_mode, qt.description
     , count(*) n
     , round(avg(qi.end_date - qi.start_date) * 24 * 60 * 60, 2) avg_seconds
     , numtodsinterval(avg(qi.end_date - qi.start_date) * 24 * 60 * 60, 'second') avg_dur
from BlueHeronData.qt_query_master qm
join blueherondata.qt_query_instance qi
 on qi.query_master_id = qm.query_master_id
join BlueHeronData.qt_query_status_type qt
 on qt.status_type_id = qi.status_type_id
 /* current month/release */
where qi.start_date >= sysdate - 30
group by trunc(qi.start_date), qt.status_type_id, qi.batch_mode, qt.description
) order by start_day desc, status_type_id desc
        ''')

        all_months = session.execute('''
select * from (
select to_char(qi.start_date, 'yyyy-mm') start_month
     , qt.status_type_id, qi.batch_mode, qt.description
     , count(*) n
     , round(avg(qi.end_date - qi.start_date) * 24 * 60 * 60, 2) avg_seconds
     , numtodsinterval(avg(qi.end_date - qi.start_date) * 24 * 60 * 60, 'second') avg_dur
from BlueHeronData.qt_query_master qm
join blueherondata.qt_query_instance qi
 on qi.query_master_id = qm.query_master_id
join BlueHeronData.qt_query_status_type qt
 on qt.status_type_id = qi.status_type_id
group by to_char(qi.start_date, 'yyyy-mm'), qt.status_type_id, qi.batch_mode, qt.description
) order by start_month desc, status_type_id desc
'''
                                )

        return dict(this_month=to_json(this_month),
                    all_months=to_json(all_months))


def _json_val(x):
    '''
    >>> _json_val(datetime.datetime(2012, 5, 10, 12, 5, 6, 804699))
    [2012, 5, 10, 12, 5, 6, 804699]
    >>> _json_val(datetime.timedelta(0, 64, 130006))
    64130
    '''
    if x is None:
        return x

    t = type(x)
    if t in (type(''), type(u''), type(1), type(True)):
        return x
    elif t is datetime.date:
        return [getattr(x, f) for f in ('year', 'month', 'day')]
    elif t is datetime.datetime:
        return [getattr(x, f) for f in ('year', 'month', 'day',
                                        'hour', 'minute', 'second',
                                        'microsecond')]
    elif t is datetime.timedelta:
        return x.microseconds / 1000 + (1000 * x.seconds)
    elif t is decimal.Decimal:
        return float(x)  # close enough for today's exercise
    else:
        return str(x)
        raise NotImplementedError('_json_val? %s' % (t))


def to_json(results):
    cols = results.keys()
    log.debug('to_json... keys: %s', cols)
    # ugh... .fetchall() and CLOBs don't seem to get along...
    out = []
    while 1:
        r = results.fetchone()
        if not r:
            break
        out.append(dict([(k, _json_val(r[k])) for k in cols]))
    return out


class Reports(PerformanceReports):
    pass
