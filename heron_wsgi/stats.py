'''stats -- HERON usage statistics views

'''

import logging
import itertools
import operator

from admin_lib import heron_policy

log = logging.getLogger(__name__)


class Reports(object):
    def configure(self, config, mount_point):
        '''Add report views to application config.
        '''
        for route_name, path, renderer, impl, perm in (
                ('usage', 'usage', 'report1.html',
                 self.show_usage_report, heron_policy.PERM_USER),
                ('query_status', 'query_status', 'query_status.html',
                 self.show_usage_current, heron_policy.PERM_USER),
                ('usage_small', 'usage_small', 'report2.html',
                 self.show_small_set_report, heron_policy.PERM_DROC),
                ):
            config.add_route(route_name, mount_point + path)
            config.add_view(impl, route_name=route_name,
                            request_method='GET', renderer=renderer,
                            permission=perm)

    def show_usage_report(self, res, req):
        usage = req.stats_reporter

        query_volume = usage.query_volume()

        def details(uid):
            try:
                a = req.agent.browser.lookup(user_id)
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
