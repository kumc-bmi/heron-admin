'''medcenter --  academic medical center directory/policy
=========================================================

A :class:`MedCenter` issues badges, and keeps Human Subjects training
records.

  >>> (m, ) = Mock.make([MedCenter])
  >>> m
  MedCenter(directory_service, training)

.. note:: See :class:`Mock` regarding the use of dependency injection
          to instantiate the :class:`MedCenter` class.

Access is logged at the :data:`logging.INFO` level.

  >>> import sys
  >>> logging.basicConfig(level=logging.INFO, stream=sys.stdout)

Issuing Notarized Badges
------------------------

A :class:`MedCenter` issues :class:`IDBadge` capabilities::

  >>> r1 = MockRequest()
  >>> caps = m.issue('john.smith', r1)
  >>> caps
  [John Smith <john.smith@js.example>]
  >>> m.audit_all(caps, PERM_ID)

  >>> js = caps[0]
  >>> js.full_name()
  'John Smith'

   >>> r2 = MockRequest()
   >>> bill = m.issue('bill.student', r2)[0]
   >>> m.is_faculty(bill)
   False

Junk:

  >>> m.audit_all(caps, 123)
  Traceback (most recent call last):
    ...
  TypeError


Human Subjects Training
-----------------------

We use an outboard service to check human subjects "chalk" training::

  >>> print _sample_chalk_settings.inifmt(CHALK_CONFIG_SECTION)
  [chalk]
  param=userid
  url=http://localhost:8080/chalk-checker

  >>> m.trained_thru(js)
  '2012-01-01'

  >>> m.trained_thru(bill)
  Traceback (most recent call last):
    ...
  LookupError


Robustness
----------

  >>> who = m.peer_badge('carol.student')
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
from datetime import timedelta

import injector
from injector import inject, provides, singleton

import rtconfig
import ldaplib
from notary import makeNotary, NotVouchable
import cache_remote

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
      >>> hits
      [John Smith <john.smith@js.example>]

      >>> hits[0].title
      'Chair of Department of Neurology'

    .. note:: KUMC uses ou for department::

        >>> hits[0].ou
        'Neurology'

    Nonsense input:

      >>> m.search(10, '', '', '')
      []
    '''
    excluded_jobcode = "24600"
    permissions = (PERM_ID,)

    @inject(searchsvc=ldaplib.LDAPService,
            trainingfn=KTrainingFunction,
            testing_faculty=KTestingFaculty)
    def __init__(self, searchsvc, trainingfn, testing_faculty):
        '''
        :param testing_faculty: testing hook for faculty badge.
        '''
        log.debug('MedCenter.__init__ again?')
        self._svc = searchsvc
        self._training = trainingfn
        self._testing_faculty = testing_faculty
        self._browser = Browser(self)
        self.__notary = makeNotary()

    def __repr__(self):
        return "MedCenter(directory_service, training)"

    def getInspector(self):
        return self.__notary.getInspector()

    def issue(self, uid, req):
        req.badge = IDBadge(self.__notary,
                            **self.directory_attributes(uid))
        return [req.badge]

    def audit_all(self, caps, permission):
        if not permission in self.permissions:
            raise TypeError

        vouch = self.__notary.getInspector().vouch

        for cap in caps:
            try:
                vouch(cap)
                return
            except NotVouchable:
                pass
        raise TypeError

    def directory_attributes(self, name):
        '''Get directory attributes.
        '''
        matches = self._svc.search('(cn=%s)' % name, Badge.attributes)
        if len(matches) != 1:  # pragma nocover
            if len(matches) == 0:
                raise KeyError(name)
            else:
                raise ValueError(name)  # ambiguous

        dn, ldapattrs = matches[0]
        return LDAPBadge._simplify(ldapattrs)

    def _search(self, max_qty, cn, sn, givenname):
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

        return self._svc.search(q, Badge.attributes)[:max_qty]

    def peer_badge(self, name):
        '''Get a badge for a peer, i.e. with no authority.
        '''
        return LDAPBadge(**self.directory_attributes(name))

    def search(self, max_qty, cn, sn, givenname):
        '''Search for peers.
        '''
        return [LDAPBadge.from_attrs(ldapattrs)
                for dn, ldapattrs in self._search(max_qty, cn, sn, givenname)]

    def is_faculty(self, alleged_badge):
        badge = self.__notary.getInspector().vouch(alleged_badge)
        log.debug('testing faculty badge kludge for %s', badge.cn)
        if ('faculty:' + badge.cn) in self._testing_faculty:  # pragma nocover
            log.info('faculty badge granted to %s by configuration', badge.cn)
            return badge

        return (badge.kumcPersonJobcode != self.excluded_jobcode
                and badge.kumcPersonFaculty == 'Y')

    def trained_thru(self, alleged_badge):
        '''
        :raises: :exc:`IOError`, :exc:`LookupError`
        '''
        badge = self.__notary.getInspector().vouch(alleged_badge)

        when = self._training(badge.cn)
        if not when:
            raise LookupError

        return when


class Browser(object):
    ''''Users get to do LDAP searches,
    but they don't get to exercise the rights of
    the users they find.
    '''
    def __init__(self, mc):
        self.lookup = mc.peer_badge
        self.search = mc.search


class NotFaculty(Exception):
    pass


class Badge(object):
    '''Convenient access to directory info.

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
    attributes = ("cn", "ou", "sn", "givenname", "title", "mail",
                  "kumcPersonFaculty", "kumcPersonJobcode")

    def __init__(self, **attrs):
        self.__attrs = attrs

    def __getattr__(self, n):
        try:
            return self.__attrs[n]
        except KeyError:
            raise AttributeError(n)

    def __repr__(self):
        return '%s %s <%s>' % (self.givenname, self.sn, self.mail)

    def full_name(self):
        return '%s %s' % (self.givenname, self.sn)

    def sort_name(self):
        return '%s, %s' % (self.sn, self.givenname)


class LDAPBadge(Badge):
    '''Utilities to handle LDAP data structures.
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


class IDBadge(LDAPBadge):
    '''Notarized badges.

      >>> (mc, ) = Mock.make([MedCenter])
      >>> r1 = MockRequest()
      >>> js = mc.issue('john.smith', r1)[0]

      >>> mc.is_faculty(js)
      True

    Note that only notarized badges are accepted:
      >>> evil = Badge(
      ...    kumcPersonJobcode='1234',
      ...    kumcPersonFaculty='Y',
      ...    cn='john.smith',
      ...    sn='Smith',
      ...    givenname='John')
      >>> mc.is_faculty(evil)
      Traceback (most recent call last):
        ...
      NotVouchable

    '''

    def __init__(self, notary, **attrs):
        assert notary
        self.__notary = notary  # has to go before LDAPBadge.__init__
        # ... due to __getattr__ magic.
        LDAPBadge.__init__(self, **attrs)

    def startVouch(self):
        self.__notary.startVouch(self)


_sample_chalk_settings = rtconfig.TestTimeOptions(dict(
        url='http://localhost:8080/chalk-checker',
        param='userid'))


class ChalkChecker(cache_remote.Cache):
    def __init__(self, ua, now, url, param,
                 ttl=timedelta(seconds=30)):
        cache_remote.Cache.__init__(self, now)

        def q_for(userid):
            def q():
                addr = url + '?' + urllib.urlencode({param: userid})
                body = ua.open(addr).read()

                if not body:  # no expiration on file
                    raise KeyError

                return ttl, body.strip()  # get rid of newline
            return q
        self.q_for = q_for

    def check(self, userid):
        return self._query(userid, self.q_for(userid), 'Chalk Training')


class _AttrDict(dict):
    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        self.__dict__ = self


class MockRequest(_AttrDict):
    def __init__(self):
        _AttrDict.__init__(self)


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


class RunTime(rtconfig.IniModule):  # pragma: nocover
    '''Configure dependencies of :class:`MedCenter`:
      - :class:`ldap.LDAPService`
      - :data:`KTrainingFunction`
      - :data:`KTestingFaculty` (for faculty testing hook)

    '''
    import datetime
    import urllib2
    _ua = urllib2.build_opener()

    @provides(KTestingFaculty)
    def no_testing_faculty(self):
        return ''

    @provides(KTrainingFunction)
    def training(self, section=CHALK_CONFIG_SECTION, ua=_ua,
                 now=datetime.datetime.now):
        rt = rtconfig.RuntimeOptions('url param'.split())
        rt.load(self._ini, section)

        cc = ChalkChecker(ua, now, rt.url, rt.param)
        return cc.check

    @classmethod
    def mods(cls, ini):
        return [cls(ini), ldaplib.RunTime(ini)]


def _integration_test():  # pragma: no cover
    logging.basicConfig(level=logging.INFO)
    (m, ) = RunTime.make(None, [MedCenter])

    if '--search' in sys.argv:
        cn, sn, givenname = sys.argv[2:5]

        print [10, cn, sn, givenname]
        print m.search(10, cn, sn, givenname)
    else:
        uid = sys.argv[1]
        req = MockRequest()
        who = m.issue(uid, req)[0]
        print who
        print "training: ", m.trained_thru(who)

        print "Once more, to check caching..."
        req = MockRequest()
        who = m.issue(uid, req)[0]
        print who
        print "training: ", m.trained_thru(who)



if __name__ == '__main__':  # pragma: no cover
    _integration_test()
