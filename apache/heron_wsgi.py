'''heron_wsgi.py -- mod_wsgi deployment details

see also heron_admin.conf
'''

import sys

prev_sys_path = list(sys.path)

# virtualenv
import site 
site.addsitedir('/usr/local/haenv/lib/python2.6/site-packages')

import os, sys
sys.path.append('/usr/local/heron_admin/')

# This doesn't work; oracle libs just have to be in /usr/local/lib or some such.
# os.environ['LD_LIBRARY_PATH']=':/usr/local/instantclient_11_2/'

#5. Set PYTHON_EGG_CACHE to an appropriate directory where the Apache user has write permission.
os.environ['PYTHON_EGG_CACHE'] = '/var/cache/haenv'

#print >>sys.stderr, 'LD_LIBRARY_PATH', os.environ['LD_LIBRARY_PATH']

from paste.script.util.logging_config import fileConfig
fileConfig('/usr/local/heron_admin/integration-test.ini')

#7. Load you application production.ini file.
from paste.deploy import loadapp
application = loadapp('config:/usr/local/heron_admin/integration-test.ini')
