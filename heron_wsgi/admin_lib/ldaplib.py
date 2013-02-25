'''ldaplib.py -- LDAP configuration and search
----------------------------------------------

Caching:

  >>> import sys
  >>> logging.basicConfig(level=logging.INFO, stream=sys.stdout)
  >>> ts = mock_directory.MockTimeSource()
  >>> ds = MockLDAP(ts, ttl=2)
  >>> ds.search("(cn=john.smith)", ['sn'])
  INFO:mock_directory:network fetch for (cn=john.smith)
  [('(cn=john.smith)', {'sn': ['Smith']})]

  >>> ds.search("(cn=john.smith)", ['sn'])
  [('(cn=john.smith)', {'sn': ['Smith']})]

  >>> ts.wait(5)
  >>> ds.search("(cn=john.smith)", ['sn'])
  INFO:mock_directory:network fetch for (cn=john.smith)
  [('(cn=john.smith)', {'sn': ['Smith']})]

Sample configuration::

  >>> print _sample_settings.inifmt(CONFIG_SECTION)
  [enterprise_directory]
  base=ou=...,o=...
  password=sekret
  url=ldaps://_ldap_host_:636
  userdn=cn=...,ou=...,o=...

Use `url=mock:mockDirectory.csv` to use a mock service rather
than a native LDAP service.
'''

import logging
from datetime import timedelta

from injector import inject, provides, singleton

import rtconfig
import mock_directory

CONFIG_SECTION = 'enterprise_directory'
log = logging.getLogger(__name__)


class LDAPService(object):
    '''See :mod:`heron_wsgi.admin_lib.mock_directory` for API details.
    '''
    def __init__(self, now, seconds):
        self.__now = now
        self._ttl = timedelta(seconds=seconds)
        self._cache = {}

    def search(self, query, attrs):
        tnow = self.__now()
        attrs = tuple(sorted(attrs))
        try:
            tfound, v = self._cache[(query, attrs)]
            if tnow - tfound <= self._ttl:
                return v
        except KeyError:
            pass

        # We're taking the time to go over the network; now is
        # a good time to prune the cache.
        for k, (t, v) in self._cache.items():
            if tnow - t > self._ttl:
                del self._cache[k]

        v = self.search_remote(query, attrs)
        self._cache[(query, attrs)] = (tnow, v)
        return v

    def search_remote(self, query, attrs):
        raise NotImplementedError('subclass must implement.')


class MockLDAP(mock_directory.MockDirectory, LDAPService):
    def __init__(self, ts, ttl):
        mock_directory.MockDirectory.__init__(self)
        LDAPService.__init__(self, ts.now, ttl)


class NativeLDAPService(LDAPService):
    '''
    .. todo:: Investigate better way to deal with SSL certs
       than putting `TLS_REQCERT allow` in /etc/ldap/ldap.conf
       (not to be confused with /etc/ldap.conf).

    '''

    def __init__(self, rt, native, now, ttl):
        LDAPService.__init__(self, now, ttl)
        self._rt = rt
        self._native = native
        self._l = None

    def _bind(self):
        rt = self._rt
        self._l = l = self._native.initialize(rt.url)
        l.simple_bind_s(rt.userdn, rt.password)
        return l

    def search_remote(self, query, attrs):
        log.info('network fetch for %s', query)
        l = self._l or self._bind()
        base = self._rt.base
        try:
            ans = l.search_s(base, self._native.SCOPE_SUBTREE, query, attrs)
        except self._native.SERVER_DOWN:
            self._l = l = self._bind()
            ans = l.search_s(base, self._native.SCOPE_SUBTREE, query, attrs)
        return ans


_sample_settings = rtconfig.TestTimeOptions(dict(
        url='ldaps://_ldap_host_:636',
        userdn='cn=...,ou=...,o=...',
        password='sekret',
        base='ou=...,o=...'))


class RunTime(rtconfig.IniModule):
    @provides((rtconfig.Options, CONFIG_SECTION))
    def opts(self):
        rt = rtconfig.RuntimeOptions('url userdn base password'.split())
        rt.load(self._ini, CONFIG_SECTION)
        return rt

    @singleton
    @provides(LDAPService)
    @inject(rt=(rtconfig.Options, CONFIG_SECTION))
    def service(self, rt):
        '''Provide native or mock LDAP implementation.

        This is demand-loaded so that the codebase can be tested
        as pure python.

        Native implementation is from python-ldap__.

        __ http://www.python-ldap.org/doc/html/ldap.html

        '''
        if rt.url.startswith('mock:'):
            res = rt.url[len('mock:'):]
            import mock_directory
            return mock_directory.MockDirectory(res)

        import ldap
        return NativeLDAPService(rt, native=ldap)


if __name__ == '__main__':  # pragma nocover
    import logging
    import sys, pprint
    ldap_query = sys.argv[1]
    attrs = sys.argv[2].split(",") if sys.argv[2:] else []

    logging.basicConfig(level=logging.INFO)
    (ls, ) = RunTime.make(None, [LDAPService])
    pprint.pprint(ls.search(ldap_query, attrs))
