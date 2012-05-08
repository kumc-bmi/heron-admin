'''medcenter --  academic medical center directory/policy
=========================================================

A :class:`MedCenter` issues and verifies identity badges and keeps
Human Subjects training records.

  >>> (m, ) = Mock.make([MedCenter])

.. note:: See :class:`Mock` regarding the use of dependency injection
          to instantiate the :class:`MedCenter` class.

Access is logged at the :data:`logging.INFO` level.

  >>> import sys
  >>> logging.basicConfig(level=logging.INFO, stream=sys.stdout)

Badge Authorization
-------------------

An object with a reference to this :class:`MedCenter` can have us
issue a :class:`Badge` on a request, once it has verified to its
satisfaction that the request is on behalf of someone in our
directory::

  >>> req = MockRequest()
  >>> req.remote_user = 'john.smith'
  >>> login_caps = m.issue(req)
  INFO:medcenter:issuing badge (LDAP): John Smith <john.smith@js.example>
  >>> req.badge
  John Smith <john.smith@js.example>

We also add to the request a sealed version of the badge that
we can audit when the `idvault` permission is exercised
(see :mod:`heron_wsgi.admin_lib.sealing`)::

  >>> login_caps
  [<MedCenter sealed box>]
  >>> login_caps[0] is req.idvault_entry
  True
  >>> m.audit(req.idvault_entry, PERM_ID)  #doctest: +ELLIPSIS
  INFO:...:MedCenter.audit(<MedCenter sealed box>, ...medcenter.idvault)

.. note:: :meth:`MedCenter.issue` and :meth:`MedCenter.audit`
          follow the :class:`heron_wsgi.cas_auth.Issuer` and
          :class:`heron_wsgi.cas_auth.Validator` protocols.

Human Subjects Training
-----------------------

We use an outboard service to check human subjects "chalk" training::

  >>> print _sample_chalk_settings.inifmt(CHALK_CONFIG_SECTION)
  [chalk]
  param=userid
  url=http://localhost:8080/chalk-checker

You can only check your own training, so you need the badge authorization::

  >>> m.training(req.idvault_entry)
  '2012-01-01'

API
---

'''

import logging
import sys
import urllib
import urllib2

import injector
from injector import inject, provides, singleton

import rtconfig
import ldaplib
import sealing

log = logging.getLogger(__name__)

KTrainingFunction = injector.Key('TrainingFunction')
KAppSecret = injector.Key('AppSecret')

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
        ''

    '''
    excluded_jobcode = "24600"
    permissions = (PERM_ID,)

    @inject(searchsvc=ldaplib.LDAPService,
            trainingfn=KTrainingFunction,
            app_secret=KAppSecret)
    def __init__(self, searchsvc, trainingfn, app_secret):
        '''
        :param app_secret: testing hook for faculty badge.
        '''
        log.debug('MedCenter.__init__ again?')
        self._svc = searchsvc
        self._training = trainingfn
        self._app_secret = app_secret
        self.sealer, self._unsealer = sealing.makeBrandPair('MedCenter')

    def __repr__(self):
        return "MedCenter(s, t)"

    def lookup(self, name):
        matches = self._svc.search('(cn=%s)' % name, Badge.attributes)
        if len(matches) != 1:
            if len(matches) == 0:
                raise KeyError(name)
            else:  # pragma nocover
                raise ValueError(name)  # ambiguous

        dn, ldapattrs = matches[0]
        return Badge.from_ldap(ldapattrs)

    def issue(self, req):
        cap = self.lookup(req.remote_user)
        auth = self.sealer.seal(cap)
        req.badge = cap
        log.info('issuing badge (LDAP): %s', cap)
        req.idvault_entry = auth
        return [auth]

    def audit(self, cap, p):
        '''Verify that self issued a capability.

        :raises: :exc:`TypeError` on failure

        See :class:`heron_wsgi.cas_auth.cas_auth.`
        '''
        log.info('MedCenter.audit(%s, %s)' % (cap, p))
        if not isinstance(cap, object):
            raise TypeError
        self._unsealer.unseal(cap)

    def read_badge(self, badgebox):
        '''Read (unseal) badge.
        '''
        return self._unsealer.unseal(badgebox)

    def faculty_badge(self, badgebox):
        '''Read faculty badge.

        :raises: :exc:`TypeError` on unsealing failure
        :raises: :exc:`NotFaculty`
        '''
        badge = self._unsealer.unseal(badgebox)

        #@@ horrible kludge for testing
        log.debug('testing faculty badge kludge for %s', badge.cn)
        if ('faculty:' + badge.cn) in self._app_secret:
            log.debug('faculty badge granted to %s by configuration', badge.cn)
            return badge

        if (badge.kumcPersonJobcode == self.excluded_jobcode
            or badge.kumcPersonFaculty != 'Y'):
            raise NotFaculty
        return badge

    def training(self, attrbox):
        return self._training(self._unsealer.unseal(attrbox)['cn'])

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
        return [Badge.from_ldap(ldapattrs)
                for dn, ldapattrs in results]


class NotFaculty(Exception):
    pass


class _AttrDict(dict):
    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        self.__dict__ = self


class Badge(_AttrDict):
    '''
      >>> js = Badge(cn='john.smith', sn='Smith', givenname='John',
      ...            mail='john.smith@example', ou='')
      >>> js
      John Smith <john.smith@example>
      >>> js.sn
      'Smith'

      >>> js.sn_typo
      Traceback (most recent call last):
      ...
      AttributeError: 'Badge' object has no attribute 'sn_typo'

    '''
    attributes = ["cn", "ou", "sn", "givenname", "title", "mail",
                  "kumcPersonFaculty", "kumcPersonJobcode"]

    @classmethod
    def from_ldap(cls, ldapattrs):
        r'''Get the 1st of each LDAP style list of values for each attribute.

          >>> Badge.from_ldap(
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
        d = dict([(n, ldapattrs.get(n, [None])[0])
                  for n in cls.attributes])

        for n in cls.attributes:
            if d[n] is None:
                log.warn('missing LDAP attribute %s for %s',
                         n, d.get('cn', '<no cn either!>'))

        return cls(d)

    def __repr__(self):
        return '%s %s <%s>' % (self.givenname, self.sn, self.mail)

    def full_name(self):
        return '%s %s' % (self.givenname, self.sn)

    def sort_name(self):
        return '%s, %s' % (self.sn, self.givenname)

    def userid(self):
        # TODO: use python property stuff?
        return self.cn


_sample_chalk_settings = rtconfig.TestTimeOptions(dict(
        url='http://localhost:8080/chalk-checker',
        param='userid'))


def chalkdb_queryfn(ini, section=CHALK_CONFIG_SECTION):  # pragma nocover.
    # not worth mocking an urlopener
    rt = rtconfig.RuntimeOptions('url param'.split())
    rt.load(ini, section)

    def training_expiration(userid):
        addr = rt.url + '?' + urllib.urlencode({rt.param: userid})
        body = urllib2.urlopen(addr).read()

        if not body:  # no expiration on file
            raise KeyError

        return body.strip()  # get rid of newline
    return training_expiration


class Mock(injector.Module, rtconfig.MockMixin):
    '''Mock up dependencies of :class:`MedCenter`:
      - :class:`ldap.LDAPService`
      - :data:`KTrainingFunction`
      - :data:`KAppSecret` (for faculty testing hook)

    .. todo:: separate LDAPService interface from implementation.
    '''

    def configure(self, binder):
        import mock_directory
        d = mock_directory.MockDirectory()

        binder.bind(ldaplib.LDAPService,
                    injector.InstanceProvider(d))
        binder.bind(KTrainingFunction,
                    injector.InstanceProvider(d.trainedThru))
        binder.bind(KAppSecret,
                    injector.InstanceProvider('sekrit'))

    @classmethod
    def login_info(self, cn):
        import warnings
        warnings.warn("deprecated", DeprecationWarning)
        req = MockRequest()
        req.remote_user = cn
        return req


class MockRequest(_AttrDict):
    pass


class RunTime(rtconfig.IniModule):
    '''Configure dependencies of :class:`MedCenter`:
      - :class:`ldap.LDAPService`
      - :data:`KTrainingFunction`
      - :data:`KAppSecret` (for faculty testing hook)

    .. todo:: separate LDAPService interface from implementation.
    '''

    @provides(KAppSecret)
    def trivial_secret(self):
        '''Note: other modules need to override KAppSecret
        '''
        return 'sekrit'

    @provides(KTrainingFunction)
    def training(self):
        return chalkdb_queryfn(self._ini, CHALK_CONFIG_SECTION)

    @classmethod
    def mods(cls, ini):
        return [cls(ini), ldaplib.RunTime(ini)]


def integration_test():  # pragma: no cover
    (m, ) = RunTime.make(None, [MedCenter])

    if '--search' in sys.argv:
        cn, sn, givenname = sys.argv[2:5]

        print [10, cn, sn, givenname]
        print m.affiliateSearch(10, cn, sn, givenname)
    else:
        uid = sys.argv[1]
        req = Mock.login_info(uid)
        m.issue(req)
        who = m.read_badge(req.idvault_entry)
        print who
        print "training: ", m.training(req.idvault_entry)


if __name__ == '__main__':  # pragma: no cover
    integration_test()
