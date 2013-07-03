'''edit_projects -- list an investigator's projects for editing
'''

from admin_lib import heron_policy
from admin_lib.noticelog import project_description


class MyProjectsView(object):
    pg_route = __name__ + '_route'
    pg_path = 'my_projects'
    template = 'my_projects.html'

    def configure(self, config, mount_point):
        '''Add report views to application config.

        >>> from pyramid.config import Configurator
        >>> config = Configurator()
        >>> my = MyProjectsView()
        >>> my.configure(config, '/tools/')
        '''

        config.add_route(self.pg_route, mount_point + self.pg_path)
        config.add_view(self.show_page, route_name=self.pg_route,
                        request_method='GET', renderer=self.template,
                        permission=heron_policy.PERM_PROJECT_EDITOR)

    def show_page(self, context, req):
        '''
        >>> mpv = MyProjectsView()

        >>> from admin_lib import heron_policy
        >>> hp, context, req = heron_policy.mock_context('john.smith')
        >>> hp.grant(req.context, heron_policy.PERM_PROJECT_EDITOR)


        >>> v = mpv.show_page(context, req)
        >>> import pprint
        >>> pprint.pprint(v)
        ... # doctest: +ELLIPSIS
        {'investigator': John Smith <john.smith@js.example>,
         'project_description': <function project_description at ...>,
         'sponsor_of': [(u'6373469799195807417',
                         (John Smith <john.smith>,
                          [Some One <some.one>, ? <carol.student>],
                          {u'approve_kuh': u'1',
                           u'approve_kumc': u'1',
                           u'approve_kupi': u'1',
                           u'date_of_expiration': u'',
                           u'full_name': u'John Smith',
                           u'name_etc_1': u'Some One',
                           u'project_title': u'Cure Warts',
                           u'user_id': u'john.smith',
                           u'user_id_1': u'some.one',
                           u'user_id_2': u'carol.student'}))],
         'sponsored_in': []}

        Check that this supplies everything the template expects::
        >>> import genshi_render
        >>> f = genshi_render.Factory({})
        >>> pg = f(v, dict(renderer_name=mpv.template))
        >>> 'Cure Warts' in pg
        True

        '''

        ed = context.project_editor

        return dict(investigator=ed._badge,
                    sponsor_of=ed.about_projects(inv=True),
                    sponsored_in=ed.about_projects(inv=False),
                    project_description=project_description)
