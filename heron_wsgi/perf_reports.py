import datetime
import decimal
import itertools
import logging
import math

from injector import inject
from sqlalchemy import orm, case, select, func, between

from admin_lib import heron_policy
from admin_lib import i2b2pm
from admin_lib.audit_usage import qi, qm, rt, qri, qt

log = logging.getLogger(__name__)


class PerformanceReports(object):
    @inject(datasrc=(orm.session.Session, i2b2pm.CONFIG_SECTION))
    def __init__(self, datasrc, cal=datetime.date.today):
        self._datasrc = datasrc
        self._cal = cal

    def configure(self, config, mount_point):
        '''Connect this view to the rest of the application

        :param config: a pyramid config thingy@@@

        .. todo:: consider allowing anonymous access to performance report.
        '''

        config.add_route('performance', mount_point + 'performance')
        config.add_view(self.show_performance, route_name='performance',
                        request_method='GET', renderer='performance.html')
                        # permission=heron_policy.PERM_STATS_REPORTER?

        config.add_route('performance_data', mount_point + 'performance_data')
        config.add_view(self.performance_data, route_name='performance_data',
                        request_method='GET', renderer='json')

        config.add_route('query_data', mount_point + 'query_data')
        config.add_view(self.query_data, route_name='query_data',
                        request_method='GET', renderer='json')

    def show_performance(self, res, req):
        order = dict(INCOMPLETE=1,
                     COMPLETED=2,
                     ERROR=3)
        perf = sorted(self.recent_query_performance(),
                      key=lambda q: order.get(q.status, 0))

        return dict(current_release=self.current_release(),
                    recent_query_performance=perf,
                    log=math.log,
                    cycle=itertools.cycle)

    def current_release(self):
        return self._datasrc().execute('''
            select project_name from I2B2PM.PM_PROJECT_DATA
            where project_id = 'BlueHeron' ''').fetchone().project_name

    def recent_query_performance(self):
        '''Show recent I2B2 queries.'''
        return self._datasrc().execute('''
select qm.query_master_id, qm.name, qm.user_id, qt.name as status,
  nvl(cast(qi.end_date as timestamp), current_timestamp) - cast(qm.create_date as timestamp) elapsed,
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

    def active_sql_stats(self):
        '''
        Bummer. I2B2 users don't have privileges to see these data.
        '''
        session = self._datasrc()
        return session.execute('''
 select b.last_load_time start_time, (b.elapsed_time / 1000000) elapsed, b.sql_id, b.sql_text --, a.*, b.*
 from v$session a
 join v$sqlarea b on a.sql_address=b.address
 where a.status = 'ACTIVE'
 and type != 'BACKGROUND'
''')

    @classmethod
    def query_data_select(cls, statuses):
        '''
        >>> print PerformanceReports.query_data_select(['ERROR'])
        ... #doctest: +NORMALIZE_WHITESPACE
        SELECT qm.query_master_id, qm.user_id, qm.name AS query_name,
               rt.name AS result_type,
               rt.description AS result_type_description,
               qri.set_size, qi.start_date, qt.description AS status,
               qi.message, qi.end_date,
               CASE WHEN (qi.end_date IS NULL) THEN NULL
                    ELSE log(:log_1, (qi.end_date - qi.start_date)
                                  * :param_1 * :param_2 * :param_3)
               END AS value, qm.request_xml
        FROM blueherondata.qt_query_master AS qm
        JOIN blueherondata.qt_query_instance AS qi
          ON qm.query_master_id = qi.query_master_id
        JOIN blueherondata.qt_query_result_instance AS qri
          ON qi.query_instance_id = qri.query_instance_id
        JOIN blueherondata.qt_query_result_type AS rt
          ON rt.result_type_id = qri.result_type_id
        JOIN blueherondata.qt_query_status_type AS qt
          ON qt.status_type_id = qi.status_type_id
        WHERE qt.description IN (:description_1)

        '''
        log_or_null = case(
            [(qi.c.end_date == None, None)],
            else_=func.log(2, (qi.c.end_date
                               - qi.c.start_date) * 24 * 60 * 60))

        stmt = select([qm.c.query_master_id,
                       qm.c.user_id,
                       qm.c.name.label('query_name'),
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
        .. todo:: vary by date, status, result_type, ...
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
where qi.start_date >= sysdate - 10
group by trunc(qi.start_date), qt.status_type_id, qi.batch_mode, qt.description
) order by start_day desc, status_type_id desc
        ''')

        if 0:  #@@
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
