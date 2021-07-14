'''jndi_util -- just enough jboss JNDI to get an Oracle connection.

'''

import os

import pkg_resources as pkg


class JBossContext(object):
    '''
    >>> os.environ["HERON_ADMIN_DB_URL"] = "oracle://BLUEHERONdata:xyzpdq@testhost:1521/DB1"

    >>> JBossContext(lambda url: url).lookup()
    'oracle://BLUEHERONdata:xyzpdq@testhost:1521/DB1'
    '''
    def __init__(self, create_engine):
        self.__create_engine = create_engine

    def lookup(self):
        url = os.environ['HERON_ADMIN_DB_URL']
        return self.__create_engine(url)
