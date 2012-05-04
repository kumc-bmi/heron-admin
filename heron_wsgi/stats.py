'''stats -- HERON usage statistics
'''

from admin_lib import heron_policy


class Report(object):
    def configure(self, config, route_name):
        '''Connect this view to the rest of the application

        :param config: a pyramid config thingy@@@
        :param route_name: a pyramid route name@@@ cite refs

        .. todo:: consider requiring DROC permissions on show_report
        '''
        config.add_view(self.show_report, route_name=route_name,
                        request_method='GET', renderer='report1.html',
                        permission=heron_policy.PERM_USER)

    def show_report(self, res, req, max_search_hits=15):
        return dict(magic_number=1)
