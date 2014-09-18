'''jndi_util -- just enough jboss JNDI to get an Oracle connection.

.. todo:: consider factoring out of rgate/i2b2hive.py
'''

from xml.etree import cElementTree as xml
import pkg_resources as pkg

from ocap_file import Readable


class JBossContext(object):
    '''
    >>> here = _MockDeployDir.make()

    >>> JBossContext(here, lambda url: url).lookup('java:/QueryToolBLUEHERONDS')
    'oracle://BLUEHERONdata:xyzpdq@testhost:1521/DB1'
    '''
    def __init__(self, jboss_deploy, create_engine):
        self.__d = jboss_deploy
        self.__create_engine = create_engine

    def lookup(self, n):
        url = 'oracle://%s:%s@%s:%s/%s' % ds_access(self.__d, n)
        return self.__create_engine(url)


class _MockDeployDir(object):
    ds = 'test-ds.xml'

    @classmethod
    def make(cls):
        return Readable('/example',
                        _MockDeployDir,
                        lambda path: [cls.ds],
                        cls.open)

    @classmethod
    def open(cls, path):
        if path != '/example/' + cls.ds:
            raise OSError(2, 'No such file or directory: %s' % path)

        return pkg.resource_stream(__name__, cls.ds)

    @staticmethod
    def abspath(p):
        return p

    @staticmethod
    def join(*pn):
        return '/'.join(pn)


def ds_access(jboss_deploy, jndi_name,
              ns='{http://www.jboss.org/ironjacamar/schema}'):
    '''Parse connection details of a jboss datasource by jndi-name.

    :param jboss_deploy: a read-capability to a jboss deploy directory.

    >>> here = _MockDeployDir.make()

    >>> ds_access(here, 'java:/QueryToolBLUEHERONDS')
    ('BLUEHERONdata', 'xyzpdq', 'testhost', '1521', 'DB1')

    Note case sensitivity:

    >>> ds_access(here, 'java:/QueryToolBlueHeronDS')
    Traceback (most recent call last):
      ...
    KeyError: 'java:/QueryToolBlueHeronDS'

    >>> ds_access(here.subRdFile('does_not_exist'), 'BLUEHERONdata')
    ... # doctest: +ELLIPSIS
    Traceback (most recent call last):
      ...
    OSError: [Errno 2] No such file or directory: ...

    :raises: XMLSyntaxError on failure to parse XML files therein,
    '''
    for f in jboss_deploy.subRdFiles():
        if not f.fullPath().endswith('-ds.xml'):
            continue
        doc = xml.parse(f.inChannel())
        srcs = doc.getroot().findall(ns + 'datasource')
        try:
            pw, url, un = ((cred.find(ns + 'password').text,
                            src.find(ns + 'connection-url').text,
                            cred.find(ns + 'user-name').text)
                           for src in srcs
                           if src.attrib['jndi-name'] == jndi_name
                           for cred in src.findall(ns + 'security')).next()
            host, port, sid = url.split('@', 1)[1].split(':', 2)
            return un, pw, host, port, sid
        except StopIteration:
            pass

    raise KeyError(jndi_name)


_token_usage = Readable
