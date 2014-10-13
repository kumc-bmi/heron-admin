'''ldaplib.py -- LDAP configuration and search
----------------------------------------------

Caching:

  >>> import sys
  >>> logging.basicConfig(level=logging.INFO, stream=sys.stdout)
  >>> ts = rtconfig.MockClock()
  >>> ds = MockLDAP(ts, ttl=2)
  INFO:cache_remote:MockLDAP@1 cache initialized
  >>> ds.search("(cn=john.smith)", ['sn'])
  INFO:cache_remote:LDAP query for ('(cn=john.smith)', ('sn',))
  INFO:cache_remote:... cached until 2011-09-02 00:00:02.500000
  [('(cn=john.smith)', {'sn': ['Smith']})]

  >>> ds.search("(cn=john.smith)", ['sn'])
  [('(cn=john.smith)', {'sn': ['Smith']})]

  >>> ts.wait(5)
  >>> ds.search("(cn=john.smith)", ['sn'])
  INFO:cache_remote:LDAP query for ('(cn=john.smith)', ('sn',))
  INFO:cache_remote:... cached until 2011-09-02 00:00:08.500000
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
from cache_remote import Cache

CONFIG_SECTION = 'enterprise_directory'
log = logging.getLogger(__name__)


class LDAPService(Cache):
    '''See :mod:`heron_wsgi.admin_lib.mock_directory` for API details.
    '''
    def __init__(self, now, ttl):
        Cache.__init__(self, now)
        self._ttl = timedelta(seconds=ttl)

    def search(self, query, attrs):
        attrs = tuple(sorted(attrs))
        return self._query((query, attrs),
                           lambda: (self._ttl,
                                    self.search_remote(query, attrs)),
                           'LDAP')

    def search_remote(self, query, attrs):
        raise NotImplementedError(
            'subclass must implement.')  # pragma: nocover


class MockLDAP(LDAPService, mock_directory.MockDirectory):
    def __init__(self, ts, ttl):
        mock_directory.MockDirectory.__init__(self)
        LDAPService.__init__(self, ts.now, ttl)

    def search_remote(self, q, attrs):
        return mock_directory.MockDirectory.search(self, q, attrs)


class NativeLDAPService(LDAPService):  # pragma: nocover
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


class RunTime(rtconfig.IniModule):  # pragma: nocover
    @provides((rtconfig.Options, CONFIG_SECTION))
    def opts(self):
        rt = rtconfig.RuntimeOptions(
            'url userdn base password executives testing_faculty'.split())
        rt.load(self._ini, CONFIG_SECTION)
        return rt

    @singleton
    @provides(LDAPService)
    @inject(rt=(rtconfig.Options, CONFIG_SECTION))
    def service(self, rt, ttl=15):
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

        import datetime
        import ldap

        return NativeLDAPService(rt, native=ldap,
                                 now=datetime.datetime.now, ttl=ttl)


def _ldap_tls_test(argv, argv_env, ldap_service):
    r'''
    e.g.
      % python ldaplib.py slapd.pem ldaps://slapd.example binddn bindpw \
        base '(cn=me)' 'mail'
    '''

    from pprint import pformat

    [cert, url, userdn, password_env, base, ldap_query, attrs] = argv[1:8]
    creds = (userdn, argv_env(password_env))
    search = ldap_service(cert, url, creds, base)
    log.info('service: %s base: %s', url, base)

    attrs = attrs.split(",")

    log.info('query: %s attrs: %s', ldap_query, attrs)
    ans = search(ldap_query, attrs)

    log.info('results: %s', pformat(ans))


def mk_ldap_service(ldap):
    def ldap_service(certfile, url, creds, base):
        def ldap_search(query, attrs):
            #ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
            ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_DEMAND)
            ldap.set_option(ldap.OPT_X_TLS_CACERTFILE, certfile)
            l = ldap.initialize(url)
            userdn, password = creds
            l.simple_bind_s(userdn, password)
            return l.search_s(base, ldap.SCOPE_SUBTREE, query, attrs)
        return ldap_search
    return ldap_service


def _integration_test(argv, ls):  # pragma nocover
    from pprint import pformat

    ldap_query = argv[1]
    attrs = argv[2].split(",") if argv[2:] else []

    log.info('query: %s attrs: %s results: %s',
             ldap_query, attrs, pformat(ls.search(ldap_query, attrs)))


if __name__ == '__main__':  # pragma nocover
    def _trusted_main():
        from os import environ
        from sys import argv
        import ldap

        logging.basicConfig(level=logging.INFO)
        (ls, ) = RunTime.make(None, [LDAPService])

        def argv_env(n):
            if n not in argv: raise IOError
            return environ[n]

        _ldap_tls_test(argv, argv_env, mk_ldap_service(ldap))
        #_integration_test(argv, ls)

        pass

    _trusted_main()
