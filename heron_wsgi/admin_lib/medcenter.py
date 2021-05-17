# -*- coding: utf-8 -*-
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

  >>> logged = rtconfig._printLogs()
  >>> import cache_remote
  >>> cache_remote.log.setLevel(level=logging.WARN)

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


allow lookup by updated kumc mail alias
---------------------------------------

  >>> r3 = MockRequest()
  >>> caps = m.authenticated('j12s34', r3)
  >>> caps
  [<MedCenter sealed box>]
  >>> m.grant(r3.context, PERM_BROWSER)

  >>> j_badge = m.idbadge(r3.context)
  >>> j_badge.full_name()
  'james smith'

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
  >>> print(logged())
  WARNING:medcenter:missing LDAP attribute kumcPersonFaculty for carol.student
  WARNING:medcenter:missing LDAP attribute kumcPersonJobcode for carol.student

  >>> who.kumcPersonJobcode is None
  True


Directory Search for Team Members
---------------------------------

Part of making oversight requests is nominating team members::

  >>> m.grant(r1.context, PERM_BROWSER)
  >>> r1.context.browser.lookup('some.one')
  Some One <some.one@js.example>
  >>> print(logged())
  WARNING:medcenter:missing LDAP attribute ou for some.one
  WARNING:medcenter:missing LDAP attribute title for some.one

  >>> r1.context.browser.search(5, 'john.smith', '', '')
  [John Smith <john.smith@js.example>]
'''

from __future__ import print_function

import json
import logging

import injector
from injector import inject, provides, singleton

import rtconfig
import ldaplib
import sealing
from notary import makeNotary
from ocap_file import WebReadable, Path

log = logging.getLogger(__name__)

TRAINING_SECTION = 'training'
# Injector keys are not shareable, so...
KTrainingFunction = (type(lambda: 1), TRAINING_SECTION)
KExecutives = injector.Key('Executives')
KTestingFaculty = injector.Key('TestingFaculty')
KStudyTeamLookup = injector.Key('StudyTeamLookup')

PERM_BROWSER = __name__ + '.browse'
PERM_BADGE = __name__ + '.badge'


@singleton
class Browser(object):
    ''''Search the directory and study teams without conferring authority.

      >>> (m, ) = Mock.make([Browser])
      >>> hits = m.search(10, 'john.smith', '', '')
      >>> hits
      [John Smith <john.smith@js.example>]

      >>> hits[0].title
      'Chair of Neurology'

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
    @inject(searchsvc=ldaplib.LDAPService,
            studyLookup=KStudyTeamLookup)
    def __init__(self, searchsvc, studyLookup):
        self._svc = searchsvc
        self._studyLookup = studyLookup

    def directory_attributes(self, name):
        '''Get directory attributes.
        '''
        matches = self._svc.search_cn(name, Badge.attributes)

        if len(matches) != 1:  # pragma nocover
            matches = self._svc.search_mail(name, Badge.attributes)
            if len(matches) != 1:
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

    def studyTeam(self, studyId):
        return self._studyLookup(studyId)


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
        #@@ log.debug('MedCenter.__init__ again?')
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
        if permission not in [PERM_BROWSER, PERM_BADGE]:
            raise TypeError

        badge = self.idbadge(context)
        context.badge = badge
        context.browser = self._browser
        context.executives = self.__executives

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

    @classmethod
    def faculty_check(cls, attrs):
        try:
            return (
                attrs['kumcPersonJobcode'] != MedCenter.excluded_jobcode
                and attrs['kumcPersonFaculty'] == 'Y')
        except KeyError:
            return None


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

    def faculty_role(self):
        return MedCenter.faculty_check(self.__attrs)


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

          >>> LDAPBadge.from_attrs(
          ...    { 'cn': ['stu.ex'],
          ...      'givenname': [u'Stu — bob'.encode('utf-8')],
          ...      'mail': ['stu@example'] })
          Stu  bob None <stu@example>

        '''
        return cls(**cls._simplify(ldapattrs))

    @classmethod
    def _simplify(cls, ldapattrs):
        # Please excuse US-centric approach.
        txt = lambda v: (v.decode('ascii', errors='ignore').encode('ascii')
                         if type(v) is str else v)
        d = AttrDict([(n, txt(ldapattrs.get(n, [None])[0]))
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
            self._is_faculty = MedCenter.faculty_check(attrs)

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
    @inject(d=ldaplib.MockDirectory, ts=rtconfig.Clock)
    def ldap(self, d, ts):
        return ldaplib.LDAPService(
            ts.now, ttl=2, rt=ldaplib._sample_settings,
            ldap=ldaplib.MockLDAP(d.records),
            flags=ldaplib.MockLDAP)

    @provides(rtconfig.Clock)
    def _time_source(self):
        return rtconfig.MockClock()

    @provides(KTrainingFunction)
    @inject(d=ldaplib.MockDirectory)
    def training_function(self, d):
        return d.latest_training

    @provides(KTestingFaculty)
    def fac(self):
        return ''

    @provides(KExecutives)
    def executives(self):
        return ('big.wig',)

    @provides(KStudyTeamLookup)
    def study_team_lookup(self):
        def lookup(_):
            raise KeyError
        return lookup


class RunTime(rtconfig.IniModule):  # pragma: nocover
    '''Configure dependencies of :class:`MedCenter`:
      - :class:`ldap.LDAPService`
      - :data:`KTrainingFunction`
      - :data:`KTestingFaculty` (for faculty testing hook)

    '''

    def __init__(self, ini, urlopener, trainingfn):
        rtconfig.IniModule.__init__(self, ini)
        self.__urlopener = urlopener
        self.__trainingfn = trainingfn
        self.label = '%s(%s, %s, %s)' % (
            self.__class__.__name__, ini, urlopener, trainingfn)

    def __repr__(self):
        return self.label

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
    def training(self):
        return self.__trainingfn

    @provides(KStudyTeamLookup)
    @inject(rt=(rtconfig.Options, ldaplib.CONFIG_SECTION))
    def study_team_lookup(self, rt):
        # TODO: share all but urllib2 stuff with Mock

        if not rt.studylookupaddr:
            raise IOError('missing studylookupaddr')

        byId = WebReadable(rt.studylookupaddr, self.__urlopener)

        def lookup(studyId):
            sub = byId.subRdFile("?id=" + studyId)
            log.info('study team lookup addr: %s', sub)
            return json.load(sub.inChannel())
        return lookup

    @classmethod
    def mods(cls, ini, timesrc, urlopener, ldap, trainingfn, **kwargs):
        return [cls(ini, urlopener, trainingfn)] + (
            ldaplib.RunTime.mods(ini, ldap, timesrc))


if __name__ == '__main__':  # pragma: no cover
    def _integration_test():  # pragma: no cover
        from io import open as io_open
        from os.path import join as joinpath, exists
        from urllib2 import build_opener
        from datetime import datetime
        from sys import argv, path as sys_path

        from sqlalchemy import create_engine
        import ldap

        cwd = Path('.', open=io_open, joinpath=joinpath, exists=exists)

        ini = cwd / 'integration-test.ini'

        if '--traincheck' in argv:
            sys_path.append('..')
            import traincheck

            trainingfn = traincheck.from_config(ini, create_engine)
        else:
            def trainingfn(who):
                return '2001-01-01'

        logging.basicConfig(level=logging.INFO)

        [m] = RunTime.make(
            [MedCenter],
            timesrc=datetime, urlopener=build_opener(),
            trainingfn=trainingfn,
            ini=ini, ldap=ldap)

        if '--search' in argv:
            cn, sn, givenname = argv[2:5]

            print([10, cn, sn, givenname])
            print(m.search(10, cn, sn, givenname))
        else:
            uid = argv[-1]
            req = MockRequest()
            m.authenticated(uid, req)
            who = m.idbadge(req.context)
            print(who)
            print("faculty? ", who.is_faculty())
            print("investigator? ", who.is_investigator())
            print("training: ", m.latest_training(who))

            print("Once more, to check caching...")
            req = MockRequest()
            m.authenticated(uid, req)
            who = m.idbadge(req.context)
            print(who)
            print("training: ", m.latest_training(who))

    _integration_test()
