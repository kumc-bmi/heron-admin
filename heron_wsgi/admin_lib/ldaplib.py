'''ldaplib.py -- LDAP configuration and search
----------------------------------------------

Caching:

  >>> logged = rtconfig._printLogs()
  >>> ts = rtconfig.MockClock()

  >>> ds = LDAPService(ts.now, ttl=2, rt=_sample_settings,
  ...                  ldap=MockLDAP(), flags=MockLDAP)
  >>> print(logged())
  INFO:cache_remote:LDAPService@1 cache initialized
  >>> ds.search_cn("john.smith", ['sn'])
  [('(cn=john.smith)', {'sn': ['Smith']})]
  >>> print(logged())
  INFO:cache_remote:LDAP query for ('(cn=john.smith)', ('sn',))
  INFO:cache_remote:... cached until 2011-09-02 00:00:02.500000

  >>> ds.search_cn("john.smith", ['sn'])
  [('(cn=john.smith)', {'sn': ['Smith']})]

  >>> ts.wait(5)
  >>> ds.search_cn("john.smith", ['sn'])
  [('(cn=john.smith)', {'sn': ['Smith']})]
  >>> print(logged())
  INFO:cache_remote:LDAP query for ('(cn=john.smith)', ('sn',))
  INFO:cache_remote:... cached until 2011-09-02 00:00:08.500000

Sample configuration::

  >>> print(_sample_settings.inifmt(CONFIG_SECTION))
  [enterprise_directory]
  base=ou=...,o=...
  certfile=LDAP_HOST_CERT.pem
  password=sekret
  url=ldaps://_ldap_host_:636
  userdn=cn=...,ou=...,o=...

The mock directory has a handful of students and faculty::

  >>> d = MockDirectory()
  >>> [(r['kumcPersonFaculty'], r['cn']) for r in d.records]
  ... #doctest: +NORMALIZE_WHITESPACE
  [('Y', 'john.smith'),
   ('N', 'bill.student'),
   ('', 'carol.student'),
   ('N', 'some.one'),
   ('N', 'big.wig'),
   ('N', 'jill.student'),
   ('N', 'koam.rin'),
   ('Y', 'trouble.maker'),
   ('N', 'act.user'),
   ('Y', 'todd.ryan')]

It supplies HSC training info::

  >>> d.latest_training('john.smith').expired
  '2012-01-01'
'''

from __future__ import print_function

from collections import namedtuple
from datetime import timedelta
from io import BytesIO
from pprint import pformat
import csv
import logging
import re

import pkg_resources as pkg
from injector import inject, provides, singleton

from cache_remote import Cache
from ocap_file import Path
import rtconfig

CONFIG_SECTION = 'enterprise_directory'
log = logging.getLogger(__name__)


class LDAPService(Cache):
    def __init__(self, now, ttl, rt, ldap, flags):
        Cache.__init__(self, now)
        self._ttl = timedelta(seconds=ttl)
        self._rt = rt
        self._ldap = ldap
        self.flags = flags
        self._l = None

    def search_cn(self, cn, attrs):
        return self._search('(cn=%s)' % quote(cn), attrs)

    def search_name_clues(self, max_qty, cn, sn, givenname, attrs):
        clauses = ['(%s=%s*)' % (n, quote(v))
                   for (n, v) in (('cn', cn),
                                  ('sn', sn),
                                  ('givenname', givenname))
                   if v]
        if len(clauses) == 0:
            return []

        if len(clauses) > 1:
            q = '(&' + (''.join(clauses)) + ')'
        else:
            q = clauses[0]

        return self._search(q, attrs)[:max_qty]

    def _search(self, query, attrs):
        attrs = tuple(sorted(attrs))
        return self._query((query, attrs),
                           lambda: (self._ttl,
                                    self.search_remote(query, attrs)),
                           'LDAP')

    def search_remote(self, query, attrs):
        ds = self._l or self._bind()
        base = self._rt.base
        try:
            ans = ds.search_s(base, self.flags.SCOPE_SUBTREE, query, attrs)
        except self.flags.SERVER_DOWN:
            self._l = ds = self._bind()
            ans = ds.search_s(base, self.flags.SCOPE_SUBTREE, query, attrs)
        return ans

    def _bind(self):
        rt = self._rt
        ldap = self._ldap
        ldap.set_option(self.flags.OPT_X_TLS_CACERTFILE, rt.certfile)
        ds = ldap.initialize(rt.url)
        ds.simple_bind_s(rt.userdn, rt.password)
        return ds


def quote(txt):
    r'''
    examples from `section 4 of RFC4515`__
    __ http://tools.ietf.org/html/rfc4515.html#section-4

    >>> print(quote('Parens R Us (for all your parenthetical needs)'))
    Parens R Us \28for all your parenthetical needs\29
    >>> print(quote('*'))
    \2a
    >>> print(quote(r'C:\MyFile'))
    C:\5cMyFile
    >>> print(quote('\x00\x00\x00\x04'))
    \00\00\00\04
    >>> print(quote(u'Lu\u010di\u0107'.encode('utf-8')))
    Lu\c4\8di\c4\87
    >>> print(quote('\x04\x02\x48\x69'))
    \04\02Hi
    '''
    hexlify = lambda m: '\\%02x' % ord(m.group(0))
    # RFC4515 asys
    # UTF1SUBSET     = %x01-27 / %x2B-5B / %x5D-7F
    # we also exclude 01-1F
    return re.sub(r'[^\x20-\x27\x2B-\x5B\x5D-\x7F]', hexlify, txt)


class MockLDAP(object):
    SCOPE_SUBTREE, OPT_X_TLS_CACERTFILE = range(2)

    class SERVER_DOWN(Exception):
        pass

    def __init__(self, records=None):
        if records is None:
            records = MockDirectory().records
        self._d = dict([(r['cn'], r) for r in records])
        self._bound = False

    def set_option(self, option, invalue):
        assert option == self.OPT_X_TLS_CACERTFILE
        assert invalue == _sample_settings.certfile

    def initialize(self, url):
        return self

    def simple_bind_s(self, username, password):
        self._bound = True

    def search_s(self, base, scope, q, attrs):
        if not self._bound:
            raise TypeError('not bound')

        log.debug('network fetch for %s', q)  # TODO: caching, .info()
        i = self._qid(q)
        try:
            record = self._d[i]
        except KeyError:
            return []
        return [('(cn=%s)' % i,
                 dict([(a, [record[a]])
                       for a in (attrs or record.keys())
                       if record[a] != '']))]

    @classmethod
    def _qid(cls, q):
        '''Extract target cn from one or two kinds of LDAP queries.

        >>> MockLDAP._qid('(cn=john.smith)')
        'john.smith'
        >>> MockLDAP._qid('(cn=john.smith*)')
        'john.smith'
        '''
        m = re.match(r'\(cn=([^*)]+)\*?\)', q)
        if m:
            return m.group(1)
        raise ValueError


_sample_settings = rtconfig.TestTimeOptions(dict(
    certfile='LDAP_HOST_CERT.pem',
    url='ldaps://_ldap_host_:636',
    userdn='cn=...,ou=...,o=...',
    password='sekret',
    base='ou=...,o=...'))


class MockDirectory(object):
    text_data = pkg.resource_string(__name__, 'mockDirectory.csv')
    records = list(csv.DictReader(BytesIO(text_data)))

    def __init__(self):
        self._d = dict([(r['cn'], r) for r in self.records])

    def latest_training(self, cn):
        expired = self._d[cn]['trainedThru']
        if not expired:
            raise LookupError(cn)
        return Training(cn, expired, expired, 'Human Subjects 101')


class Training(namedtuple('Training',
                          'username expired completed course'.split())):
    pass


class RunTime(rtconfig.IniModule):  # pragma: nocover
    def __init__(self, ini, ldap):
        rtconfig.IniModule.__init__(self, ini)
        self.__ldap = ldap
        self.label = '%s(%s, %s)' % (self.__class__.__name__, ini, ldap)

    def __repr__(self):
        return self.label

    @provides((rtconfig.Options, CONFIG_SECTION))
    def opts(self):
        return self.get_options(
            ('url certfile userdn base password'
             ' studylookupaddr'
             ' executives testing_faculty').split(),
            CONFIG_SECTION)

    @singleton
    @provides(LDAPService)
    @inject(rt=(rtconfig.Options, CONFIG_SECTION),
            timesrc=rtconfig.Clock)
    def service(self, rt, timesrc,
                ttl=15):
        '''Provide native or mock LDAP implementation.

        This is demand-loaded so that the codebase can be tested
        as pure python.

        Native implementation is from python-ldap__.

        __ http://www.python-ldap.org/doc/html/ldap.html

        '''
        flags = self.__ldap
        return LDAPService(timesrc.now, ttl=ttl, rt=rt,
                           ldap=self.__ldap, flags=flags)

    @classmethod
    def mods(cls, ini, ldap, timesrc, **kwargs):
        return [cls(ini, ldap), rtconfig.RealClockInjector(timesrc)]


if __name__ == '__main__':  # pragma nocover
    def _script():  # pragma nocover
        from io import open as io_open
        from os.path import join as joinpath, exists
        from sys import argv, stdout
        from datetime import datetime

        import ldap

        logging.basicConfig(level=logging.INFO)
        cwd = Path('.', open=io_open, joinpath=joinpath, exists=exists)

        ldap_query, config_fn = argv[1:3]
        ini = cwd / config_fn
        if argv[3:]:
            attrs = argv[3].split(",")
        else:
            attrs = []

        [ls] = RunTime.make([LDAPService],
                            ini=ini,
                            ldap=ldap, timesrc=datetime)

        print(pformat(ls._search(ldap_query, attrs)), file=stdout)

    _script()
