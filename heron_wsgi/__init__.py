'''heron_wsgi/__init__.py -- Pyramid main() for the HERON admin interface
'''
# python stdlib http://docs.python.org/library/
import logging

# modules from PyPi http://pypi.python.org/pypi
import injector
#from sqlalchemy import engine_from_config

# modules in this package
import heron_srv

KAppSettings = injector.Key('AppSettings')

log = logging.getLogger(__name__)

def main(global_config, **settings):
    return heron_srv.app_factory(global_config, **settings)


if __name__ == '__main__':
    import sys
    webapp_ini, admin_ini = sys.argv[1:3]
    logging.basicConfig(level=logging.DEBUG)
    main({},   # for debugging
         webapp_ini= webapp_ini,
         admin_ini=admin_ini)
