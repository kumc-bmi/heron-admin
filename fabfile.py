'''fabfile -- automate deployment of HERON admin changes

.. todo:: automate initial deployment
.. todo:: automate deployment of config changes

.. note:: Some changes require restarting apache; we don't support
          that yet because we don't want to require sudo rights.

.. todo:: consider restarting apache
'''

__author__ = 'Dan Connolly'
__copyright__ = 'Copyright (c) 2012 University of Kansas Medical Center'
__license__ = 'MIT'
__contact__ = 'http://informatics.kumc.edu/'

from os import path
from fabric.api import task, local


@task
def deploy_hg_tip(usrlocal='/usr/local',
                  app='heron-admin'):
    dest = path.join(usrlocal, app)
    local('mkdir -p %s' % dest)
    local('hg archive %s' % dest)
    # hg archive sets permissions to 755 or 644.
    # We need them group-writeable.
    # This should only involve files that this user created.
    local('find %s -not -perm -g=w -print0 | '
          'xargs -0 chmod g+w' % dest)
