'''stats -- HERON usage statistics
'''

from injector import inject
from sqlalchemy import orm

from admin_lib import heron_policy

CONFIG_SECTION = 'i2b2pm'


class Report(object):
    @inject(datasrc=(orm.session.Session, CONFIG_SECTION))
    def __init__(self, datasrc):
        self._datasrc = datasrc

    def configure(self, config, route_name):
        '''Connect this view to the rest of the application

        :param config: a pyramid config thingy@@@
        :param route_name: a pyramid route name@@@ cite refs

        .. todo:: consider requiring DROC permissions on show_report
        '''
        config.add_view(self.show_usage_report, route_name=route_name,
                        request_method='GET', renderer='report1.html',
                        permission=heron_policy.PERM_USER)

    def show_usage_report(self, res, req, max_search_hits=15):
        # we might want this... params = req.GET
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
