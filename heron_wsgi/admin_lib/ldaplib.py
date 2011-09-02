'''ldaplib.py -- LDAP configuration and search

We expect configuration a la::

  [enterprise_directory]
  url=ldaps://_ldap_host_:636
  userDn= cn=...,ou=...,o=...
  password= ...
  base= ou=...,o=...

'''
import ldap # http://www.python-ldap.org/doc/html/ldap.html

import config

class LDAPService(object):
    '''
    Haven't found a better way to deal with SSL certs
    than putting `TLS_REQCERT allow` in /etc/ldap/ldap.conf
    (not to be confused with /etc/ldap.conf)

    '''

    def __init__(self, ini, section):
        rt = config.RuntimeOptions('url userdn base password'.split())
        rt.load(ini, section)
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


def _integration_test(ini='integration-test.ini', section='enterprise_directory'):
    return LDAPService(ini, section)


if __name__ == '__main__':
    import sys, pprint
    ldap_query = sys.argv[1]
    attrs = sys.argv[2].split(",") if sys.argv[2:] else []
    ls = _integration_test()
    pprint.pprint(ls.search(ldap_query, attrs))
