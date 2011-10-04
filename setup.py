'''setup.py -- heron_wsgi package information
'''

__author__ = 'Dan Connolly <dconnolly@kumc.edu>'
__copyright__ = '(c) 2011 University of Kansas Medical Center'
__contact__ = 'http://informatics.kumc.edu/work/wiki/RequestTracking'
__license__ = 'Apache 2'
__version__ = '0.1'


import os
import sys

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = '@@TODO'  #open(os.path.join(here, 'README.txt')).read()
CHANGES = '@@TODO' #open(os.path.join(here, 'CHANGES.txt')).read()

requires = [
    'SQLAlchemy',
    'cx_Oracle',
    'MySQL-python',
    'lxml',
    'python-ldap',
    'beaker',
    'paste',
    'genshi',
    'injector',
    'PasteDeploy',
    'PasteScript',
    'pyinotify'
    ]

if sys.version_info[:3] < (2,5,0):
    requires.append('pysqlite')

setup(name='heron_wsgi',
      version=__version__,
      description='HERON regulatory enforcement web interface',
      long_description=README + '\n\n' +  CHANGES,
      classifiers=[
        "Programming Language :: Python",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        ],
      author=__author__.split('<')[0][:-1],
      author_email=__author__.split('<')[1][:-1],
      url=__contact__,
      license=__license__,
      keywords='web wsgi hipaa policy enforcement',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
# TODO: learn how test_suite works
#     test_suite='heron_acct',
      install_requires = requires,
      entry_points = {
        'console_scripts':
            ['logwatch=heron_wsgi.logwatch:main'],
        'paste.app_factory':
            ['main = heron_wsgi.heron_srv:app_factory']
        },
      #paster_plugins=['pyramid'],
      )

