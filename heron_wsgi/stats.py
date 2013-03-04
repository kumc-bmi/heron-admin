'''stats -- HERON usage statistics views

'''

import logging
import itertools
import operator

from admin_lib import medcenter

log = logging.getLogger(__name__)


class Reports(object):
    def configure(self, config, mount_point):
        '''Add report views to application config.

        >>> from pyramid.config import Configurator
        >>> config = Configurator()
        >>> Reports().configure(config, '/reports')
        '''
        for route_name, path, renderer, impl, perm in (
                ('usage', 'usage', 'report1.html',
                 self.show_usage_report, medcenter.PERM_ID),
                ('query_status', 'query_status', 'query_status.html',
                 self.show_usage_current, medcenter.PERM_ID),
                ('usage_small', 'usage_small', 'report2.html',
                 self.show_small_set_report, medcenter.PERM_ID),
                ):
            config.add_route(route_name, mount_point + path)
            config.add_view(impl, route_name=route_name,
                            request_method='GET', renderer=renderer,
                            permission=perm)

    def show_usage_report(self, res, req):
        '''
        >>> from pyramid.testing import DummyRequest
        >>> r = Reports()
        >>> req = DummyRequest()
        >>> (mc, ) = medcenter.Mock.make([medcenter.MedCenter])
        >>> mc.issue('john.smith', req)  # set up browser
        [John Smith <john.smith@js.example>]
        >>> req.stats_reporter = MockAggregateUsage()

        >>> r.show_usage_report(None, req)  # doctest: +NORMALIZE_WHITESPACE
        {'total_number_of_queries': 100,
         'queries_by_month':
          [{'y': 2011, 'm': 5, 'users': 8, 'qty': 80},
           {'y': 2011, 'm': 6, 'users': 0, 'qty': 90}],
         'query_volume':
          [{'user_id': 'john.smith', 'last_month': 10, 'last_year': 20,
            'last_quarter': 20, 'two_weeks': 5,
            'full_name': 'John Smith', 'all_time': 20}],
         'roles': {'john.smith':
                   'Chair of Department of Neurology, Neurology'},
         'cycle': <type 'itertools.cycle'>}

        '''
        usage = req.stats_reporter

        query_volume = usage.query_volume()

        def details(uid):
            try:
                a = req.browser.lookup(user_id)
                return '%s, %s' % (a.title, a.ou)
            except KeyError:
                return ''

        user_ids = set([row.user_id for row in query_volume])
        roles = dict([(user_id, details(user_id))
                      for user_id in user_ids])

        return dict(total_number_of_queries=usage.total_number_of_queries(),
                    query_volume=query_volume,
                    roles=roles,
                    queries_by_month=usage.queries_by_month(),
                    cycle=itertools.cycle)

    def show_usage_current(self, res, req):
        usage = req.stats_reporter
        return dict(queries=usage.current_queries(),
                    cycle=itertools.cycle)

    def show_small_set_report(self, res, req):
        audit = req.agent.sensitive_usage()
        return dict(
            summary=audit.patient_set_queries(recent=True, small=True),
            detail=itertools.groupby(audit.small_set_concepts(),
                                     operator.itemgetter('query_master_id')),
            cycle=itertools.cycle)


class MockAggregateUsage(object):
    def total_number_of_queries(self):
        return 100

    def queries_by_month(self):
        AD = medcenter._AttrDict
        return [AD(y=y, m=m, qty=qty, users=users)
                for y, m, qty, users in
                ((2011, 5, 80, 8),
                 (2011, 6, 90, 0))]

    def query_volume(self, recent=False):
        AD = medcenter._AttrDict
        return [AD(full_name='John Smith',
                   user_id='john.smith',
                   two_weeks=5, last_month=10,
                   last_quarter=20, last_year=20,
                   all_time=20)]

