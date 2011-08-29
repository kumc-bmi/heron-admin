'''medcenter.py -- academic medical center directory/policy
'''

import sys
import os
import ConfigParser

# http://www.python-ldap.org/doc/html/ldap.html
import ldap

# consider using snake-guice for testability
# http://code.google.com/p/snake-guice/wiki/GuiceBasics

class MedCenter(object):
    def __init__(self, searchfn):
        self._search = searchfn

    def affiliate(self, name):
        matches = self._search('(cn=%s)' % name,
                               ['cn','sn','givenname','mail'])
        if len(matches) != 1:
            if len(matches) == 0:
                raise KeyError, name
            else:
                raise ValueError, name  # ambiguous

        dn, x = matches[0]

        return AccountHolder(x)


class AccountHolder(object):
    def __init__(self, attrs):
        self._userid = attrs['cn'][0]
        self._sn = attrs['sn'][0]
        self._givenname = attrs['givenname'][0]
        self._mail = attrs['mail'][0]

    def __str__(self):
        return '%s, %s <%s>' % (self._sn, self._givenname, self._mail)


def ldap_searchfn(config, section):
    p = ConfigParser.SafeConfigParser()
    p.read(config)
    opts = dict(p.items(section))
    l = ldap.initialize(opts['url'])
    # TODO: figure out how to configure openssl to handle self-signed certs
    # work-around: use `TLS_REQCERT allow` in /etc/ldap/ldap.conf
    # (not to be confused with /etc/ldap.conf)
    l.simple_bind_s(opts['userdn'], opts['password'])
    base = opts['base']

    def search(query, attrs):
        return l.search_s(base, ldap.SCOPE_SUBTREE, query, attrs)

    return search

def _integration_test():
    ini, section, uid = sys.argv[1:4]
    s = ldap_searchfn(ini, section)
    m = MedCenter(s)
    print m.affiliate(uid)

if __name__ == '__main__':
    _integration_test()
