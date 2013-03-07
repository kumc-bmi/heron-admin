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
  >>> caps = m.authenticated('john.smith', r1)
  >>> caps
  [<MedCenter sealed box>]
  >>> m.grant(r1.context, PERM_BROWSER)

  >>> js = m.idbadge(r1.context)
  >>> js.full_name()
  'John Smith'

   >>> r2 = MockRequest()
   >>> _ = m.authenticated('bill.student', r2)[0]
   >>> bill = m.idbadge(r2.context)
   >>> bill.is_faculty()
   False

Junk:

  >>> r2.context.remote_user = 123
  >>> m.grant(r2.context, PERM_BROWSER)
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


Directory Search for Team Members
---------------------------------

Part of making oversight requests is nominating team members::

  >>> m.grant(r1.context, PERM_BROWSER)
  >>> r1.context.browser.lookup('some.one')
  WARNING:medcenter:missing LDAP attribute ou for some.one
  WARNING:medcenter:missing LDAP attribute title for some.one
  Some One <some.one@js.example>

  >>> r1.context.browser.search(5, 'john.smith', '', '')
  [John Smith <john.smith@js.example>]


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
import sealing
from notary import makeNotary
import cache_remote

log = logging.getLogger(__name__)

KTrainingFunction = injector.Key('TrainingFunction')
KExecutives = injector.Key('Executives')
KTestingFaculty = injector.Key('TestingFaculty')

CHALK_CONFIG_SECTION = 'chalk'
PERM_BROWSER = __name__ + '.browse'


@singleton
class Browser(object):
    ''''Search the directory, without conferring authority.

      >>> (m, ) = Mock.make([Browser])
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
    @inject(searchsvc=ldaplib.LDAPService)
    def __init__(self, searchsvc):
        self._svc = searchsvc

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

    def lookup(self, name):
        '''Get a badge for a peer, i.e. with no authority.
        '''
        return LDAPBadge(**self.directory_attributes(name))

    def search(self, max_qty, cn, sn, givenname):
        '''Search for peers.
        '''
        return [LDAPBadge.from_attrs(ldapattrs)
                for dn, ldapattrs in self._search(max_qty, cn, sn, givenname)]


@singleton
class MedCenter(object):
    '''Enterprise authorization and search.

    .. note:: This implements the :class:`heron_wsgi.cas_auth.Issuer` protocol.
    '''
    excluded_jobcode = "24600"

    @inject(browser=Browser,
            trainingfn=KTrainingFunction,
            executives=KExecutives,
            testing_faculty=KTestingFaculty)
    def __init__(self, browser, trainingfn,
                 testing_faculty, executives):
        '''
        :param testing_faculty: testing hook for faculty badge.
        '''
        log.debug('MedCenter.__init__ again?')
        self._training = trainingfn
        self._testing_faculty = testing_faculty
        self.__executives = executives
        self._browser = browser
        self.search = browser.search
        self.peer_badge = browser.lookup
        self.__notary = makeNotary()
        self.__sealer, self.__unsealer = sealing.makeBrandPair(
            self.__class__.__name__)

    def __repr__(self):
        return "MedCenter(directory_service, training)"

    def getInspector(self):
        return self.__notary.getInspector()

    def authenticated(self, uid, req):
        cred = self.__sealer.seal(uid)
        req.context.remote_user = cred
        return [cred]

    def grant(self, context, permission):
        if permission is not PERM_BROWSER:
            raise TypeError

        badge = self.idbadge(context)
        if not badge.is_investigator():
            raise TypeError

        context.browser = self._browser

    def idbadge(self, context):
        '''
        @raises AttributeError if context lacks remote user;
                TypeError on failure to authenticate context.remote_user
        '''
        uid = self.__unsealer.unseal(context.remote_user)  # raises TypeError

        return IDBadge(self.__notary, uid in self.__executives,
                       **self._browser.directory_attributes(uid))

    def trained_thru(self, alleged_badge):
        '''
        :raises: :exc:`IOError`, :exc:`LookupError`
        '''
        badge = self.__notary.getInspector().vouch(alleged_badge)

        when = self._training(badge.cn)
        if not when:
            raise LookupError

        return when


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
        d = _AttrDict([(n, ldapattrs.get(n, [None])[0])
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
      >>> js = mc.authenticated('john.smith', r1)[0]

      >>> mc.idbadge(r1.context).is_faculty()
      True

    Note that only notarized badges are accepted:
      >>> evil = Badge(
      ...    kumcPersonJobcode='1234',
      ...    kumcPersonFaculty='Y',
      ...    cn='john.smith',
      ...    sn='Smith',
      ...    givenname='John')
      >>> mc.trained_thru(evil)
      Traceback (most recent call last):
        ...
      NotVouchable

    '''

    def __init__(self, notary, is_executive=False, **attrs):
        assert notary
        self.__notary = notary  # has to go before LDAPBadge.__init__
        # ... due to __getattr__ magic.
        self._is_executive = is_executive
        LDAPBadge.__init__(self, **attrs)

    def startVouch(self):
        self.__notary.startVouch(self)

    def is_faculty(self):
        try:
            return (self.kumcPersonJobcode != MedCenter.excluded_jobcode
                    and self.kumcPersonFaculty == 'Y')
        except AttributeError:
            return False

    def is_executive(self):
        return self._is_executive

    def is_investigator(self):
        return self.is_faculty() or self.is_executive()

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
        self.context = _AttrDict()


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

    @provides(KExecutives)
    def executives(self):
        return ('big.wig',)


class RunTime(rtconfig.IniModule):  # pragma: nocover
    '''Configure dependencies of :class:`MedCenter`:
      - :class:`ldap.LDAPService`
      - :data:`KTrainingFunction`
      - :data:`KTestingFaculty` (for faculty testing hook)

    '''
    import datetime
    import urllib2
    _ua = urllib2.build_opener()

    @provides(KExecutives)
    @inject(rt=(rtconfig.Options, ldaplib.CONFIG_SECTION))
    def executives(self, rt):
        es = rt.executives.split()
        assert es  # watch out for old config version
        return es

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
        m.authenticated(uid, req)
        who = m.idbadge(req.context)
        print who
        print "faculty? ", who.is_faculty()
        print "investigator? ", who.is_investigator()
        print "training: ", m.trained_thru(who)

        print "Once more, to check caching..."
        req = MockRequest()
        m.authenticated(uid, req)
        who = m.idbadge(req.context)
        print who
        print "training: ", m.trained_thru(who)


if __name__ == '__main__':  # pragma: no cover
    _integration_test()
