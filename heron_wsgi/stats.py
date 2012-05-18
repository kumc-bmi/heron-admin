'''stats -- HERON usage statistics

'''

import logging

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

    def configure(self, config, mount_point):
        '''Connect this view to the rest of the application

        :param config: a pyramid config thingy@@@

        .. todo:: consider requiring DROC permissions on show_report
        '''
        config.add_route('usage', mount_point + 'usage')
        config.add_view(self.show_usage_report, route_name='usage',
                        request_method='GET', renderer='report1.html',
                        permission=heron_policy.PERM_USER)

    def show_usage_report(self, res, req):
        connection = self._datasrc()
        result = connection.execute('''
            select count(*) as total_number_of_queries
            from BLUEHERONDATA.qt_query_master
        ''')
        data = result.fetchall()

        if len(data) == 1:
            count = data[0].total_number_of_queries
        else:
            raise ValueError('expected 1 row; got: %s' % len(data))

        # overall query volume by user
        result = connection.execute('''
            select user_id as users, count(*) as number_of_queries
            from BLUEHERONDATA.qt_query_master qqm
            group by user_id
            order by number_of_queries desc''')
        query_volume = result.fetchall()

        return dict(total_number_of_queries=count,
                    query_volume=query_volume)


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
                                        'hour', 'minute', 'second', 'microsecond')]
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
