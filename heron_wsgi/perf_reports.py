import datetime
import decimal
import itertools
import logging
import math

from admin_lib import heron_policy

log = logging.getLogger(__name__)


class PerformanceReports(object):

    def configure(self, config, mount_point):
        '''Connect this view to the rest of the application

        :param config: a pyramid config
        '''

        config.add_route('performance', mount_point + 'performance')
        config.add_view(self.show_performance, route_name='performance',
                        request_method='GET', renderer='performance.html',
                        permission=heron_policy.PERM_STATS_REPORTER)

    def show_performance(self, context, req):
        order = dict(INCOMPLETE=1,
                     COMPLETED=2,
                     ERROR=3)

        usage = context.stats_reporter

        perf = sorted(usage.recent_query_performance(),
                      key=lambda q: order.get(q.status, 0))

        return dict(current_release=usage.current_release(),
                    recent_query_performance=perf,
                    current_sessions=usage.current_sessions(),
                    log=math.log,
                    cycle=itertools.cycle)


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
