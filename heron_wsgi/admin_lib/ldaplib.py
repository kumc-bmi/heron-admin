'''ldaplib.py -- LDAP configuration and search

Sample configuration::

  >>> print _sample_settings.inifmt(CONFIG_SECTION)
  [enterprise_directory]
  base=ou=...,o=...
  password=sekret
  url=ldaps://_ldap_host_:636
  userdn=cn=...,ou=...,o=...

'''
import ldap # http://www.python-ldap.org/doc/html/ldap.html
import injector
from injector import inject, provides

import config

CONFIG_SECTION='enterprise_directory'


class LDAPService(object):
    '''
    Haven't found a better way to deal with SSL certs
    than putting `TLS_REQCERT allow` in /etc/ldap/ldap.conf
    (not to be confused with /etc/ldap.conf)

    '''

    @inject(rt=(config.Options, CONFIG_SECTION))
    def __init__(self, rt):
        self._rt = rt
        self._l = None

    def bind(self):
        rt = self._rt
        self._l = l = ldap.initialize(rt.url)
        l.simple_bind_s(rt.userdn, rt.password)
        return l

    def search(self, query, attrs):
        l = self._l or self.bind()
        base = self._rt.base
        try:
            ans = l.search_s(base, ldap.SCOPE_SUBTREE, query, attrs)
        except ldap.SERVER_DOWN:
            self._l = l = self.bind()
            ans = l.search_s(base, ldap.SCOPE_SUBTREE, query, attrs)
        return ans


_sample_settings = config.TestTimeOptions(dict(
        url='ldaps://_ldap_host_:636',
        userdn='cn=...,ou=...,o=...',
        password='sekret',
        base='ou=...,o=...'))


class RunTime(injector.Module):
    def __init__(self, ini='integration-test.ini'):
        injector.Module.__init__(self)
        self._ini = ini

    @provides((config.Options, CONFIG_SECTION))
    def opts(self):
        rt = config.RuntimeOptions('url userdn base password'.split())
        rt.load(self._ini, CONFIG_SECTION)
        return rt

    @classmethod
    def make(cls):
        depgraph = injector.Injector([cls()])
        return depgraph.get(LDAPService)

if __name__ == '__main__':  # pragma nocover
    import sys, pprint
    ldap_query = sys.argv[1]
    attrs = sys.argv[2].split(",") if sys.argv[2:] else []

    ls = RunTime.make()
    pprint.pprint(ls.search(ldap_query, attrs))
