'''medcenter --  academic medical center directory/policy
=========================================================

A :class:`MedCenter` looks up badges, delegates to affiliates, and keeps
Human Subjects training records.

  >>> (m, ) = Mock.make([MedCenter])

.. note:: See :class:`Mock` regarding the use of dependency injection
          to instantiate the :class:`MedCenter` class.

Access is logged at the :data:`logging.INFO` level.

  >>> import sys
  >>> logging.basicConfig(level=logging.INFO, stream=sys.stdout)

Affiliate Authorization
-----------------------

A :class:`MedCenter` delegates authority to an :class:`Affiliate`::

  >>> js = Affiliate({}, 'john.smith', m)
  >>> js.full_name()
  INFO:mock_directory:network fetch for (cn=john.smith)
  'John Smith'
  >>> js
  John Smith <john.smith@js.example>

Human Subjects Training
-----------------------

We use an outboard service to check human subjects "chalk" training::

  >>> print _sample_chalk_settings.inifmt(CHALK_CONFIG_SECTION)
  [chalk]
  param=userid
  url=http://localhost:8080/chalk-checker

  >>> js.trained_thru()
  '2012-01-01'

.. todo:: document failure modes of `trained_thru`

Regression testing
------------------

  >>> who = m.lookup('carol.student')
  INFO:mock_directory:network fetch for (cn=carol.student)
  WARNING:medcenter:missing LDAP attribute kumcPersonFaculty for carol.student
  WARNING:medcenter:missing LDAP attribute kumcPersonJobcode for carol.student

  >>> who.kumcPersonJobcode is None
  True


API
---

'''

import logging
import sys
import urllib

import injector
from injector import inject, provides, singleton

import rtconfig
import ldaplib
import sealing

log = logging.getLogger(__name__)

KTrainingFunction = injector.Key('TrainingFunction')
KTestingFaculty = injector.Key('TestingFaculty')

CHALK_CONFIG_SECTION = 'chalk'
PERM_ID = __name__ + '.idvault'


@singleton
class MedCenter(object):
    '''Enterprise authorization and search.

    .. note:: This implements the :class:`heron_wsgi.cas_auth.Issuer` protocol.

    To search the directory, without conferring authority::
      >>> (m, ) = Mock.make([MedCenter])
      >>> hits = m.search(10, 'john.smith', '', '')
      INFO:mock_directory:network fetch for (cn=john.smith*)
      >>> hits
      [John Smith <john.smith@js.example>]

      >>> hits[0].title
      'Chair of Department of Neurology'

    .. note:: KUMC uses ou for department::

        >>> hits[0].ou
        'Neurology'

    '''
    excluded_jobcode = "24600"
    permissions = (PERM_ID,)

    @inject(searchsvc=ldaplib.LDAPService,
            trainingfn=KTrainingFunction,
            testing_faculty=KTestingFaculty)
    def __init__(self, searchsvc, trainingfn, testing_faculty):
        '''
        :param app_secret: testing hook for faculty badge.
        '''
        log.debug('MedCenter.__init__ again?')
        self._svc = searchsvc
        self._training = trainingfn
        self._testing_faculty = testing_faculty
        self._browser = Browser(self)

    def __repr__(self):
        return "MedCenter(s, t)"

    def get(self, name):
        matches = self._svc.search('(cn=%s)' % name, Badge.attributes)
        if len(matches) != 1:
            if len(matches) == 0:
                raise KeyError(name)
            else:  # pragma nocover
                raise ValueError(name)  # ambiguous

        dn, ldapattrs = matches[0]
        return LDAPBadge._simplify(ldapattrs)

    def lookup(self, name):
        return LDAPBadge(**self.get(name))

    def is_faculty(self, badge):
        log.debug('testing faculty badge kludge for %s', badge.cn)
        if ('faculty:' + badge.cn) in self._testing_faculty:
            log.info('faculty badge granted to %s by configuration', badge.cn)
            return badge

        return (badge.kumcPersonJobcode != self.excluded_jobcode
                and badge.kumcPersonFaculty == 'Y')

    def search(self, max_qty, cn, sn, givenname):
        clauses = ['(%s=%s*)' % (n, v)
                   for (n, v) in (('cn', cn),
                                  ('sn', sn),
                                  ('givenname', givenname))
                   if v]
        if len(clauses) == 0:
            return ()

        if len(clauses) > 1:
            q = '(&' + (''.join(clauses)) + ')'
        else:
            q = clauses[0]

        results = self._svc.search(q, Badge.attributes)[:max_qty]
        return [LDAPBadge.from_attrs(ldapattrs)
                for dn, ldapattrs in results]


class Browser(object):
    ''''Users get to do LDAP searches,
    but they don't get to exercise the rights of
    the users they find.
    '''
    def __init__(self, mc):
        self.lookup = mc.lookup
        self.search = mc.search


class NotFaculty(Exception):
    pass


class Badge(object):
    attributes = ("cn", "ou", "sn", "givenname", "title", "mail",
                  "kumcPersonFaculty", "kumcPersonJobcode")

    def __repr__(self):
        return '%s %s <%s>' % (self.givenname, self.sn, self.mail)

    def full_name(self):
        return '%s %s' % (self.givenname, self.sn)

    def sort_name(self):
        return '%s, %s' % (self.sn, self.givenname)

    def userid(self):
        import warnings
        warnings.warn("Badge.userid is deprecated", DeprecationWarning)
        return self.cn


class LDAPBadge(Badge):
    '''
      >>> js = LDAPBadge(cn='john.smith', sn='Smith', givenname='John',
      ...                mail='john.smith@example', ou='')
      >>> js
      John Smith <john.smith@example>
      >>> js.sn
      'Smith'

      >>> js.sn_typo
      Traceback (most recent call last):
      ...
      AttributeError: sn_typo

    '''
    @classmethod
    def from_attrs(cls, ldapattrs):
        r'''Get the 1st of each LDAP style list of values for each attribute.

          >>> LDAPBadge.from_attrs(
          ...    {'kumcPersonJobcode': ['1234'],
          ...     'kumcPersonFaculty': ['Y'],
          ...      'cn': ['john.smith'],
          ...      'title': ['Chair of Department of Neurology'],
          ...      'sn': ['Smith'],
          ...      'mail': ['john.smith@js.example'],
          ...      'ou': [''],
          ...      'givenname': ['John']})
          John Smith <john.smith@js.example>
        '''
        return cls(**cls._simplify(ldapattrs))

    @classmethod
    def _simplify(cls, ldapattrs):
        d = dict([(n, ldapattrs.get(n, [None])[0])
                  for n in cls.attributes])

        for n in cls.attributes:
            if d[n] is None:
                log.warn('missing LDAP attribute %s for %s',
                         n, d.get('cn', '<no cn either!>'))

        return d

    def __init__(self, **attrs):
        self.__attrs = attrs

    def __getattr__(self, n):
        try:
            return self.__attrs[n]
        except KeyError:
            raise AttributeError(n)


class Affiliate(Badge):
    '''
      >>> (mc, ) = Mock.make([MedCenter])
      >>> session_cache = {}
      >>> js = Affiliate(session_cache, 'john.smith', mc)

      >>> js.sn
      INFO:mock_directory:network fetch for (cn=john.smith)
      'Smith'

    Network fetches are cached::

      >>> (js.sn, js.givenname)
      ('Smith', 'John')

      >>> js.sn_typo
      Traceback (most recent call last):
      ...
      AttributeError: sn_typo

      >>> mc.is_faculty(js)
      True
      >>> bill = Affiliate({}, 'bill.student', mc)
      >>> mc.is_faculty(bill)
      INFO:mock_directory:network fetch for (cn=bill.student)
      False

      >>> js.trained_thru()
      '2012-01-01'
      >>> bill.trained_thru()
      Traceback (most recent call last):
        ...
      LookupError


      >>> Affiliate.cache_sizes_sum() < Affiliate.cache_max
      True
    '''

    cache_max = 4000  # TODO: cite sources about session cookie limitations
    cache_sizes = dict(kumcPersonJobcode=20,
                       kumcPersonFaculty=1,
                       cn=60,
                       title=80,
                       sn=60,
                       mail=80,
                       ou=60,
                       givenname=20)

    @classmethod
    def cache_sizes_sum(cls):
        return sum([len(k) + v for k, v in cls.cache_sizes.iteritems()])

    def __init__(self, cache, cn, mc):
        Badge.__init__(self)
        cache['cn'] = cn
        self.__cache = cache
        self.__cn = cn
        self.__mc = mc
        self.browser = mc._browser

    def __getattr__(self, n):
        if not n in Badge.attributes:
            raise AttributeError(n)
        cache = self.__cache
        try:
            return cache[n]
        except KeyError:
            pass
        d = self.__mc.get(self.__cn)
        for k, v in d.iteritems():
            self._put(k, v)
        return d[n]

    def __contains__(self, k):
        return k in self.__cache

    def __getitem__(self, k):
        return self.__cache[k]

    def _put(self, k, v):
        assert type(v) in (type(''), type(1), type(None)), (k, type(v))
        cache = self.__cache
        if len(str(v)) <= self.cache_sizes[k]:
            cache[k] = v
        return v

    def trained_thru(self):
        '''
        :raises: :exc:`IOError`, :exc:`LookupError`
        '''
        when = self.__mc._training(self.__cn)

        if not when:
            raise LookupError
        return when


_sample_chalk_settings = rtconfig.TestTimeOptions(dict(
        url='http://localhost:8080/chalk-checker',
        param='userid'))


class Mock(injector.Module, rtconfig.MockMixin):
    '''Mock up dependencies of :class:`MedCenter`:
      - :class:`ldap.LDAPService`
      - :data:`KTrainingFunction`
      - :data:`KTestingFaculty` (for faculty testing hook)

    '''

    def configure(self, binder):
        import mock_directory
        d = mock_directory.MockDirectory()

        binder.bind(ldaplib.LDAPService,
                    injector.InstanceProvider(d))
        binder.bind(KTrainingFunction,
                    injector.InstanceProvider(d.trainedThru))
        binder.bind(KTestingFaculty,
                    injector.InstanceProvider(''))


class RunTime(rtconfig.IniModule):
    '''Configure dependencies of :class:`MedCenter`:
      - :class:`ldap.LDAPService`
      - :data:`KTrainingFunction`
      - :data:`KTestingFaculty` (for faculty testing hook)

    '''
    import urllib2
    _ua = urllib2.build_opener()

    @provides(KTestingFaculty)
    def no_testing_faculty(self):
        return ''

    @provides(KTrainingFunction)
    def training(self, section=CHALK_CONFIG_SECTION, ua=_ua):

        rt = rtconfig.RuntimeOptions('url param'.split())
        rt.load(self._ini, section)

        def training_expiration(userid):
            addr = rt.url + '?' + urllib.urlencode({rt.param: userid})
            body = ua.open(addr).read()

            if not body:  # no expiration on file
                raise KeyError

            return body.strip()  # get rid of newline

        return training_expiration

    @classmethod
    def mods(cls, ini):
        return [cls(ini), ldaplib.RunTime(ini)]


def integration_test():  # pragma: no cover
    logging.basicConfig(level=logging.INFO)
    (m, ) = RunTime.make(None, [MedCenter])

    if '--search' in sys.argv:
        cn, sn, givenname = sys.argv[2:5]

        print [10, cn, sn, givenname]
        print m.search(10, cn, sn, givenname)
    else:
        uid = sys.argv[1]
        who = Affiliate({}, uid, m)
        print who
        print "training: ", who.trained_thru()


if __name__ == '__main__':  # pragma: no cover
    integration_test()
