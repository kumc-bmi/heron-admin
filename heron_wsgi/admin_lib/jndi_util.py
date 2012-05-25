'''jndi_util -- just enough jboss JNDI to get an Oracle connection.

.. todo:: consider factoring out of rgate/i2b2hive.py
'''

from lxml import etree

from ocap_file import Readable


class JBossContext(object):
    def __init__(self, jboss_deploy, create_engine):
        self.__d = jboss_deploy
        self.__create_engine = create_engine

    def lookup(self, n):
        url = 'oracle://%s:%s@%s:%s/%s' % ds_access(self.__d, n)
        return self.__create_engine(url)


def ds_access(jboss_deploy, jndi_name):
    '''Parse connection details of a jboss datasource by jndi-name.

    :param jboss_deploy: a read-capability to a jboss deploy directory.

    >>> import os
    >>> here = Readable('.', os.path, os.listdir, open)

    >>> ds_access(here, 'QueryToolBLUEHERONDS')
    ('BLUEHERONdata', 'xyzpdq', 'bmidev1', '1521', 'bmid')

    Note case sensitivity:

    >>> ds_access(here, 'QueryToolBlueHeronDS')
    Traceback (most recent call last):
      ...
    KeyError: 'QueryToolBlueHeronDS'

    >>> ds_access(here.subRdFile('does_not_exist'), 'BLUEHERONdata')
    Traceback (most recent call last):
      ...
    OSError: [Errno 2] No such file or directory: './does_not_exist'

    :raises: XMLSyntaxError on failure to parse XML files therein,
    '''
    for f in jboss_deploy.subRdFiles():
        if not f.fullPath().endswith('-ds.xml'):
            continue
        doc = etree.parse(f.inChannel())
        src_expr = ('/datasources/local-tx-datasource[jndi-name/text()="%s"]' %
                    jndi_name)
        try:
            src = doc.xpath(src_expr)[0]
            un = src.xpath('user-name/text()')[0]
            pw = src.xpath('password/text()')[0]
            url = src.xpath('connection-url/text()')[0]
            host, port, sid = url.split('@', 1)[1].split(':', 2)
            return un, pw, host, port, sid
        except IndexError:
            pass

    raise KeyError(jndi_name)


_token_usage = Readable
