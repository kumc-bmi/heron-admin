# python stdlib http://docs.python.org/library/
import logging

# modules from PyPi http://pypi.python.org/pypi
import injector
from injector import inject
import pyramid
from pyramid.config import Configurator
from pyramid.authorization import ACLAuthorizationPolicy
from sqlalchemy import engine_from_config

from pyramid.events import NewRequest
from pyramid.events import subscriber

# modules in this package
from admin_lib.config import Options
import cas_auth
import heron_srv

KAppSettings = injector.Key('AppSettings')

log = logging.getLogger(__name__)

def main(global_config, **settings):
    """Build the Pyramid WSGI for the HERON admin interface
    """
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
        return cas_auth.RunTime.deps(webapp_ini) + [
            heron_srv.RunTime(webapp_ini, admin_ini),
            RunTime(settings)]

    @classmethod
    def depgraph(cls, settings):
        deps = cls.deps(settings)
        log.debug('deps: %s', deps)
        return injector.Injector(deps)


class HeronAdminConfig(Configurator):
    @inject(guard=cas_auth.Validator,
            settings=KAppSettings,
            cas_rt=(Options, cas_auth.CONFIG_SECTION))
    def __init__(self, guard, settings, cas_rt):
        pwho = guard.policy(cas_rt.app_secret),
        pwhat = cas_auth.CapabilityStyle(guard, cas_auth.PERMISSION)
        Configurator.__init__(self, settings=settings,
                              authentication_policy= pwho,
                              authorization_policy=pwhat,
                              default_permission=cas_auth.PERMISSION
                              )

        self.add_static_view('av', 'heron_wsgi:htdocs-heron/av/',
                             cache_max_age=3600)

        self.scan('heron_wsgi')  # @@ use __name__ somehow?
