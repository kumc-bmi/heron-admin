'''heron_wsgi/__init__.py -- Pyramid main() for the HERON admin interface
'''
# python stdlib http://docs.python.org/library/
import logging

# modules from PyPi http://pypi.python.org/pypi
import injector
from injector import inject
import pyramid
from pyramid.config import Configurator
from pyramid.authorization import ACLAuthorizationPolicy
from sqlalchemy import engine_from_config

# modules in this package
from admin_lib.config import Options
import cas_auth
import heron_srv
from admin_lib import i2b2pm  #@@
import genshi_render

KAppSettings = injector.Key('AppSettings')

log = logging.getLogger(__name__)

def main(global_config, **settings):
    #@@engine = engine_from_config(settings, 'sqlalchemy.')
    #initialize_sql(engine)

    depgraph = RunTime.depgraph(settings)
    config = depgraph.get(HeronAdminConfig)

    return config.make_wsgi_app()


class RunTime(injector.Module):
    def __init__(self, settings):
        self._settings = settings

    def configure(self, bindings):
        bindings.bind(KAppSettings, self._settings)

    @classmethod
    def deps(cls, settings):
        webapp_ini = settings['webapp_ini']
        admin_ini = settings['admin_ini']
        return (cas_auth.RunTime.mods(webapp_ini) + 
                [c(admin_ini) for c in i2b2pm.IntegrationTest.deps()] +  #@@ should be heron_srv?
                [heron_srv.RunTime(webapp_ini, admin_ini),
                 RunTime(settings)])

    @classmethod
    def depgraph(cls, settings):
        log.debug('settings: %s', settings)
        deps = cls.deps(settings)
        log.debug('deps: %s', deps)
        return injector.Injector(deps)


class HeronAdminConfig(Configurator):
    @inject(guard=cas_auth.Validator,
            settings=KAppSettings,
            cas_rt=(Options, cas_auth.CONFIG_SECTION),
            clv=heron_srv.CheckListView)
    def __init__(self, guard, settings, cas_rt, clv):
        Configurator.__init__(self, settings=settings)
        guard.configure(self, cas_rt.app_secret)
        cap_style = cas_auth.CapabilityStyle(guard, cas_auth.PERMISSION)
        self.set_authorization_policy(cap_style)
        self.add_static_view('av', 'heron_wsgi:htdocs-heron/av/',
                             cache_max_age=3600)

        self.add_renderer(name='.html', factory=genshi_render.Factory)

        self.add_route('heron_home', '')
        self.add_route('logout', 'logout')
        self.add_route('saa', 'saa_survey')
        self.add_route('team_done', 'team_done')
        self.add_route('i2b2_login', '/i2b2')
        self.add_route('oversight', 'build_team.html')

        clv.configure(self, 'heron_home')


if __name__ == '__main__':
    import sys
    webapp_ini, admin_ini = sys.argv[1:3]
    logging.basicConfig(level=logging.DEBUG)
    main({},   # for debugging
         webapp_ini= webapp_ini,
         admin_ini=admin_ini)
