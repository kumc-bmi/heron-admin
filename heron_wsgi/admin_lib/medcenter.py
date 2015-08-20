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
  >>> logging.getLogger('cache_remote').setLevel(level=logging.WARN)

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

We use an database view to check human subjects research training::

  >>> m.latest_training(js).expired
  '2012-01-01'

  >>> m.latest_training(bill)
  Traceback (most recent call last):
    ...
  LookupError: bill.student


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
from contextlib import contextmanager

import injector
from injector import inject, provides, singleton
from sqlalchemy.engine.url import make_url

import rtconfig
import ldaplib
import sealing
import mock_directory
from notary import makeNotary
from heron_wsgi.traincheck.traincheck import TrainingRecordsRd

log = logging.getLogger(__name__)

KTrainingFunction = injector.Key('TrainingFunction')
KExecutives = injector.Key('Executives')
KTestingFaculty = injector.Key('TestingFaculty')

TRAINING_SECTION = 'training'
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

      >>> m.lookup('nobody-by-this-cn')
      Traceback (most recent call last):
        ....
      KeyError: 'nobody-by-this-cn'


    Nonsense input:

      >>> m.search(10, '', '', '')
      []

      >>> m.search(10, '**goofy name**', '', '')
      []

    '''
    @inject(searchsvc=ldaplib.LDAPService)
    def __init__(self, searchsvc):
        self._svc = searchsvc

    def directory_attributes(self, name):
        '''Get directory attributes.
        '''
        matches = self._svc.search_cn(name, Badge.attributes)

        if len(matches) != 1:  # pragma nocover
            if len(matches) == 0:
                raise KeyError(name)
            else:
                raise ValueError(name)  # ambiguous

        dn, ldapattrs = matches[0]
        return LDAPBadge._simplify(ldapattrs)

    def _search(self, max_qty, cn, sn, givenname):
        return self._svc.search_name_clues(max_qty, cn, sn, givenname,
                                           Badge.attributes)

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
        :raises: TypeError on failure to authenticate context.remote_user
        '''
        try:
            remote_user = context.remote_user
        except AttributeError:
            raise TypeError

        uid = self.__unsealer.unseal(remote_user)  # raises TypeError

        return IDBadge(self.__notary, uid in self.__executives,
                       uid in self._testing_faculty,
                       **self._browser.directory_attributes(uid))

    def latest_training(self, alleged_badge):
        '''
        :raises: :exc:`IOError`, :exc:`LookupError`
        '''
        badge = self.__notary.getInspector().vouch(alleged_badge)

        info = self._training(badge.cn)

        return info


class NotFaculty(TypeError):
    # subclass TypeError for compatibility with cas_auth grant()
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
        d = AttrDict([(n, ldapattrs.get(n, [None])[0])
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
      >>> mc.latest_training(evil)
      Traceback (most recent call last):
        ...
      NotVouchable

    '''

    def __init__(self, notary, is_executive=False, testing_faculty=False,
                 **attrs):
        assert notary
        self.__notary = notary  # has to go before LDAPBadge.__init__
        # ... due to __getattr__ magic.
        self._is_executive = is_executive
        self._is_faculty = testing_faculty
        if testing_faculty:
            log.info('%s considered faculty by testing override.',
                     attrs.get('cn', 'CN???'))
        else:
            try:
                self._is_faculty = (
                    attrs['kumcPersonJobcode'] != MedCenter.excluded_jobcode
                    and attrs['kumcPersonFaculty'] == 'Y')
            except KeyError:
                pass

        LDAPBadge.__init__(self, **attrs)

    def startVouch(self):
        self.__notary.startVouch(self)

    def is_faculty(self):
        return self._is_faculty

    def is_executive(self):
        return self._is_executive

    def is_investigator(self):
        return self.is_faculty() or self.is_executive()


class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        self.__dict__ = self


class MockRequest(AttrDict):
    def __init__(self):
        AttrDict.__init__(self)
        self.context = AttrDict()


class Mock(injector.Module, rtconfig.MockMixin):
    '''Mock up dependencies of :class:`MedCenter`:
      - :class:`ldap.LDAPService`
      - :data:`KTrainingFunction`
      - :data:`KTestingFaculty` (for faculty testing hook)

    '''

    @provides(ldaplib.LDAPService)
    @inject(d=mock_directory.MockDirectory, ts=rtconfig.Clock)
    def ldap(self, d, ts):
        return ldaplib.LDAPService(
            ts.now, ttl=2, rt=ldaplib._sample_settings,
            ldap=ldaplib.MockLDAP(d.records),
            flags=ldaplib.MockLDAP)

    @provides(rtconfig.Clock)
    def _time_source(self):
        return rtconfig.MockClock()

    @provides(KTrainingFunction)
    @inject(d=mock_directory.MockDirectory)
    def training_function(self, d):
        return d.latest_training

    @provides(KTestingFaculty)
    def fac(self):
        return ''

    @provides(KExecutives)
    def executives(self):
        return ('big.wig',)


class RunTime(rtconfig.IniModule):  # pragma: nocover
    '''Configure dependencies of :class:`MedCenter`:
      - :class:`ldap.LDAPService`
      - :data:`KTrainingFunction`
      - :data:`KTestingFaculty` (for faculty testing hook)

    '''

    @provides(KExecutives)
    @inject(rt=(rtconfig.Options, ldaplib.CONFIG_SECTION))
    def executives(self, rt):
        es = rt.executives.split()
        assert es  # watch out for old config version
        return es

    @provides(KTestingFaculty)
    @inject(rt=(rtconfig.Options, ldaplib.CONFIG_SECTION))
    def testing_faculty(self, rt):
        tf = (rt.testing_faculty or '').split()
        log.info('testing faculty: %s', tf)
        return tf

    @provides(KTrainingFunction)
    def training(self, section=TRAINING_SECTION):
        from sqlalchemy import create_engine

        rt = rtconfig.RuntimeOptions('url'.split())
        rt.load(self._ini, section)

        u = make_url(rt.url)
        redcapdb = (None if u.drivername == 'sqlite' else 'redcap')

        # Address connection timeouts using pool_recycle
        # ref http://docs.sqlalchemy.org/en/rel_1_0/dialects/mysql.html#connection-timeouts  # noqa
        trainingdb = create_engine(u, pool_recycle=3600)
        account = lambda: trainingdb.connect(), u.database, redcapdb

        tr = TrainingRecordsRd(account)

        return tr.__getitem__

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
        print "training: ", m.latest_training(who)

        print "Once more, to check caching..."
        req = MockRequest()
        m.authenticated(uid, req)
        who = m.idbadge(req.context)
        print who
        print "training: ", m.latest_training(who)


if __name__ == '__main__':  # pragma: no cover
    _integration_test()
