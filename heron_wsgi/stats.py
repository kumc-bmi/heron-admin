'''stats -- HERON usage statistics
'''

from injector import inject
from sqlalchemy import orm
import datetime
import decimal

from admin_lib import heron_policy

CONFIG_SECTION = 'i2b2pm'


class Machine(object):
    '''Machine Interface

    See :class:`heron_wsgi.powerbox.LinuxMachine` for implementation.
    '''
    def load(self):
        '''Report load average(s) on the machine

        :returntype: list of (minutes, load) tuples.
        '''
        return [(1, 0.00), (5, 0.00), (15, 0.00)]


class Report(object):
    @inject(datasrc=(orm.session.Session, CONFIG_SECTION),
            machine=Machine)
    def __init__(self, datasrc, machine):
        self._datasrc = datasrc
        self._machine = machine

    def configure(self, config, mount_point):
        '''Connect this view to the rest of the application

        :param config: a pyramid config thingy@@@

        .. todo:: consider requiring DROC permissions on show_report
        .. todo:: consider allowing anonymous access to performance report.
        '''
        config.add_route('usage', mount_point + 'usage')
        config.add_view(self.show_usage_report, route_name='usage',
                        request_method='GET', renderer='report1.html',
                        permission=heron_policy.PERM_USER)

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

    def show_performance(self, res, req):
        return {}

    def query_data(self, res, req):
        connection = self._datasrc()
        #@@ just the last week
        qt = connection.execute('''SELECT qm.query_master_id,
          qm.request_xml,
          qi.start_date,
          qm.user_id,
          qm.name AS query_name ,
          qt.description status,
          qi.end_date,
          case when qi.end_date is null then null
               when qi.end_date = qi.start_date then null
               else log(2, (qi.end_date - qi.start_date) * 24 * 60 * 60)
          end "value"
        FROM BlueHeronData.qt_query_master qm
        JOIN BLUEHERONDATA.QT_QUERY_INSTANCE qi
        ON qi.query_master_id = qm.query_master_id
        JOIN BlueHeronData.qt_query_status_type qt
        ON qt.status_type_id = qi.status_type_id
        where qi.start_date between sysdate - 7 and sysdate
        order by qi.start_date
        ''')
        #@@where qi.start_date between date '2011-09-01' and date '2011-09-08'

        return dict(queries=to_json(qt))

    def performance_data(self, res, req):
        connection = self._datasrc()
        this_month = connection.execute('''
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

        all_months = connection.execute('''
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

    def _machine_load(self):
        ''' @@dead code '''
        return dict(machine_load=self._machine.load())


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
        raise NotImplementedError('_json_val? %s / %s' % (x, t))


def to_json(results):
    cols = results.keys()
    return [dict([(k, _json_val(r[k])) for k in cols]) for r in results.fetchall()]
