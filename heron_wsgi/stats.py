'''stats -- HERON usage statistics views
----------------------------------------

'''

import logging
import itertools
import operator

from admin_lib import medcenter
from admin_lib import heron_policy

log = logging.getLogger(__name__)


class Reports(object):
    def __repr__(self):
        return '%s()' % self.__class__.__name__

    def configure(self, config, mount_point):
        '''Add report views to application config.

        >>> from pyramid.config import Configurator
        >>> config = Configurator()
        >>> Reports().configure(config, '/reports')
        '''
        for route_name, path, renderer, impl, perm in (
                ('usage', 'usage', 'report1.html',
                 self.show_usage_report, heron_policy.PERM_STATS_REPORTER),
                ('query_status', 'query_status', 'query_status.html',
                 self.show_usage_current, heron_policy.PERM_DROC_AUDIT),
                ('usage_small', 'usage_small', 'report2.html',
                 self.show_small_set_report, heron_policy.PERM_DROC_AUDIT),
        ):
            config.add_route(route_name, mount_point + path)
            config.add_view(impl, route_name=route_name,
                            request_method='GET', renderer=renderer,
                            permission=perm)

    def show_usage_report(self, context, req):
        '''
        >>> hp, context, req = heron_policy.mock_context('john.smith')
        >>> r = Reports()
        >>> hp.grant(context, heron_policy.PERM_STATS_REPORTER)

        >>> context.stats_reporter = MockAggregateUsage()  # Kludge

        >>> v = r.show_usage_report(context, req)
        >>> from pprint import pprint
        >>> pprint(v)
        {'cycle': <type 'itertools.cycle'>,
         'queries_by_month': [{'m': 5, 'qty': 80, 'users': 8, 'y': 2011},
                              {'m': 6, 'qty': 90, 'users': 0, 'y': 2011}],
         'query_volume': [{'all_time': 20,
                           'full_name': 'John Smith',
                           'last_month': 10,
                           'last_quarter': 20,
                           'last_year': 20,
                           'two_weeks': 5,
                           'user_id': 'john.smith'}],
         'roles': {'john.smith': 'Chair of Neurology, Neurology'},
         'total_number_of_queries': 100}


        Check that this supplies everything the template expects::
        >>> import genshi_render
        >>> f = genshi_render.Factory({})
        >>> pg = f(v, dict(renderer_name='report1.html'))
        >>> 'John Smith' in pg and 'Chair of' in pg
        True

        '''
        usage = context.stats_reporter
        browser = context.browser

        query_volume = usage.query_volume()

        def details(uid):
            try:
                a = browser.lookup(user_id)
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

    def show_usage_current(self, context, req):
        usage = context.droc_audit
        return dict(queries=usage.current_queries(),
                    cycle=itertools.cycle)

    def show_small_set_report(self, context, req):
        '''
        >>> hp, context, req = heron_policy.mock_context('big.wig')
        >>> r = Reports()
        >>> hp.grant(context, heron_policy.PERM_DROC_AUDIT)

        >>> context.droc_audit = MockDROCAudit()  # Kludge

        >>> ssr = r.show_small_set_report(context, req)
        >>> from pprint import pprint
        >>> pprint(ssr)
        ... # doctest: +ELLIPSIS
        {'cycle': <type 'itertools.cycle'>,
         'detail': <itertools.groupby object at ...>,
         'projects': [(u'6373469799195807417',
                       (John Smith <john.smith>, u'Cure Warts', ''))],
         'sponsorships': {'john.smith': ([],
                                         [(u'6373469799195807417',
                                           John Smith <john.smith>,
                                           u'Cure Warts',
                                           '')]),
                          'some.one': ([(u'6373469799195807417',
                                         John Smith <john.smith>,
                                         u'Cure Warts',
                                         '')],
                                       [])},
         'summary': [{'create_date': datetime.date(2000, 1, 1),
                      'full_name': 'Some One',
                      'name': 'smallpox',
                      'query_master_id': 1,
                      'set_size': 9,
                      'user_id': 'some.one'},
                     {'create_date': datetime.date(2000, 1, 2),
                      'full_name': 'Some One',
                      'name': 'smallpox2',
                      'query_master_id': 10,
                      'set_size': 8,
                      'user_id': 'some.one'},
                     {'create_date': datetime.date(2000, 2, 1),
                      'full_name': 'John Smith',
                      'name': 'malaria',
                      'query_master_id': 2,
                      'set_size': 5,
                      'user_id': 'john.smith'}]}

        Make sure we don't call about_sponsorships more than we need to.
        >>> len(r._about(context.decision_records, ssr['summary']))
        2

        Check that this supplies everything the template expects::
        >>> import genshi_render
        >>> f = genshi_render.Factory({})
        >>> pg = f(ssr, dict(renderer_name='report2.html'))
        >>> 'Malaria' in pg
        True

        '''

        audit = context.droc_audit
        dr = context.decision_records

        summary = audit.patient_set_queries(recent=True, small=True)
        sponsorships = dict(self._about(dr, summary))
        # making a dict throws out duplicates
        projects_collate = dict([(record, (inv, title, desc))
                                 for spair in sponsorships.values()
                                 for slist in spair
                                 for record, inv, title, desc in slist])

        projects = sorted(projects_collate.items(), key=lambda x: -int(x[0]))

        return dict(
            summary=summary,
            sponsorships=sponsorships,
            projects=projects,
            detail=itertools.groupby(audit.small_set_concepts(),
                                     operator.itemgetter('query_master_id')),
            cycle=itertools.cycle)

    def _about(self, dr, summary):
        return [(user_id,
                 (dr.about_sponsorships(user_id),
                  dr.about_sponsorships(user_id, inv=True)))
                for user_id in
                set([q.user_id for q in summary])]


class MockAggregateUsage(object):
    def total_number_of_queries(self):
        return 100

    def queries_by_month(self):
        AD = medcenter.AttrDict
        return [AD(y=y, m=m, qty=qty, users=users)
                for y, m, qty, users in
                ((2011, 5, 80, 8),
                 (2011, 6, 90, 0))]

    def query_volume(self, recent=False):
        AD = medcenter.AttrDict
        return [AD(full_name='John Smith',
                   user_id='john.smith',
                   two_weeks=5, last_month=10,
                   last_quarter=20, last_year=20,
                   all_time=20)]


class MockDROCAudit(object):
    def patient_set_queries(self, small, recent):
        from datetime import date
        AD = medcenter.AttrDict
        return [AD(full_name='Some One',
                   user_id='some.one',
                   query_master_id=1, name='smallpox',
                   create_date=date(2000, 1, 1),
                   set_size=9),
                AD(full_name='Some One',
                   user_id='some.one',
                   query_master_id=10, name='smallpox2',
                   create_date=date(2000, 1, 2),
                   set_size=8),
                AD(full_name='John Smith',
                   user_id='john.smith',
                   query_master_id=2, name='malaria',
                   create_date=date(2000, 2, 1),
                   set_size=5)]

    def small_set_concepts(self):
        from datetime import date
        AD = medcenter.AttrDict
        return [AD(user_id='some.one',
                   query_master_id=1,
                   create_date=date(2000, 1, 1),
                   query_name='smallpox',
                   item_name='Smallpox',
                   tooltip='Horrible Diseases : Smallpox',
                   item_key='\\\\i2b2\\Horrible Diseases\\Smallpox\\'),
                AD(user_id='john.smith',
                   query_master_id=2,
                   create_date=date(2000, 2, 1),
                   query_name='malaria',
                   item_name='Malaria',
                   tooltip='Horrible Diseases : Malaria',
                   item_key='\\\\i2b2\\Horrible Diseases\\Malaria\\')]
