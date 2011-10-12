'''medcenter --  academic medical center directory/policy
==========================================================

Login Capabilities
------------------

Suppose we have a login capability (see cas_auth.Issuer)::
  >>> import sys
  >>> logging.basicConfig(level=logging.INFO, stream=sys.stdout)
  >>> m = Mock.make()

  >>> box, req = Mock.login_info(m, 'john.smith')
  >>> box, req
  (<MedCenter sealed box>, {})

Then we'll issue a login capability:
  >>> login_caps = m.issue(box, req)
  >>> login_caps
  [<MedCenter sealed box>]

Note that it has to be our own login capability::
  >>> foreign_box = Mock.make().sealer.seal('john.smith')
  >>> m.issue(foreign_box, req)
  Traceback (most recent call last):
  ...
  TypeError

And we'll issue no capabilities unless the login capability bears
the correct application secret::
  >>> boxx = m.sealer.seal(('john.smith', 'wrong_sekrit'))
  >>> m.issue(boxx, req)
  WARNING:medcenter:unexpected app_secret [wrong_sekrit]
  []


Directory Lookup
----------------

We can exercise an enterprise directory capability::

  >>> b1 = m.read_badge(req.idvault_entry)
  >>> b1
  John Smith <john.smith@js.example>
  >>> b1.title
  'Chair of Department of Neurology'

Note: KUMC uses ou for department.
  >>> b1.ou
  ''

  >>> m.search(10, 'john.smith', '', '')
  [John Smith <john.smith@js.example>]

Human Subjects Training
-----------------------

We use an outboard service to check human subjects "chalk" training::

  >>> print _sample_chalk_settings.inifmt(CHALK_CONFIG_SECTION)
  [chalk]
  param=userid
  url=http://localhost:8080/chalk-checker

  >>> m.training(req.idvault_entry)
  '2012-01-01'

'''

import logging
import os
import sys
import urllib
import urllib2

import injector
from injector import inject, provides, singleton

import config
import ldaplib
import sealing

log = logging.getLogger(__name__)

KTrainingFunction = injector.Key('TrainingFunction')
KAppSecret = injector.Key('AppSecret')

CHALK_CONFIG_SECTION='chalk'
PERM_ID=__file__ + '.idvault'

@singleton
class MedCenter(object):
    '''This implemeted the cas_auth.Issuer protocol,
    though we're avoiding an actual dependency in that direction just now.
    '''
    excluded_jobcode = "24600"
    permissions=(PERM_ID,)

    @inject(searchsvc=ldaplib.LDAPService,
            trainingfn=KTrainingFunction,
            app_secret=KAppSecret)
    def __init__(self, searchsvc, trainingfn, app_secret):
        log.debug('MedCenter.__init__ again?')
        self._svc = searchsvc
        self._training = trainingfn
        self._app_secret = app_secret
        self.sealer, self._unsealer = sealing.makeBrandPair('MedCenter')

    def __repr__(self):
        return "MedCenter(s, t)"

    def _lookup(self, name):
        matches = self._svc.search('(cn=%s)' % name, Badge.attributes)
        if len(matches) != 1:
            if len(matches) == 0:
                raise KeyError, name
            else: # pragma nocover
                raise ValueError, name  # ambiguous

        dn, ldapattrs = matches[0]
        return Badge.from_ldap(ldapattrs)

    def issue(self, loginbox, req):
        u, s = self._unsealer.unseal(loginbox)
        if s != self._app_secret:
            log.warn('unexpected app_secret [%s]', s)
            return []
        cap = self.sealer.seal(self._lookup(u))
        req.idvault_entry = cap
        return [cap]

    def audit(self, cap, p):
        '''See cas_auth.
        '''
        log.info('MedCenter.audit(%s, %s)' % (cap, p))
        if not isinstance(cap, object):
            raise TypeError
        self._unsealer.unseal(cap)

    def lookup(self, namebox):  #@@ dead code?
        name = self._unsealer.unseal(namebox)
        return self.sealer.seal(self._lookup(name))

    def read_badge(self, badgebox):
        '''Read (unseal) badge.
        '''
        return self._unsealer.unseal(badgebox)

    def faculty_badge(self, badgebox):
        '''Read faculty badge.
        @raises: TypeError on unsealing failure
        @raises: NotFaculty
        '''
        badge = self._unsealer.unseal(badgebox)
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


class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        self.__dict__ = self


class Badge(AttrDict):
    '''
      >>> js = Badge(cn='john.smith', sn='Smith', givenname='John',
      ...            mail='john.smith@example')
      >>> js
      John Smith <john.smith@example>
      >>> js.sn
      'Smith'
      >>> js.sn_typo
      Traceback (most recent call last):
      ...
      AttributeError: 'Badge' object has no attribute 'sn_typo'


    Note: KUMC uses ou for department.
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
        return cls(
            **dict([(n, ldapattrs.get(n, [None])[0])
                    for n in cls.attributes]))

    def __repr__(self):
        return '%s %s <%s>' % (self.givenname, self.sn, self.mail)

    def userid(self):
        # TODO: use python property stuff?
        return self.cn


_sample_chalk_settings = config.TestTimeOptions(dict(
        url='http://localhost:8080/chalk-checker',
        param='userid'))


def chalkdb_queryfn(ini, section=CHALK_CONFIG_SECTION):  # pragma nocover. not worth mocking an urlopener
    rt = config.RuntimeOptions('url param'.split())
    rt.load(ini, section)

    def training_expiration(userid):
        addr = rt.url + '?' + urllib.urlencode({rt.param: userid})
        body = urllib2.urlopen(addr).read()

        if not body:  # no expiration on file
            raise KeyError

        return body.strip()  # get rid of newline
    return training_expiration


class ModuleHelper(object):
    @classmethod
    def depgraph(cls):
        return injector.Injector(cls.mods())

    @classmethod
    def make(cls):
        return cls.depgraph().get(MedCenter)


class Mock(injector.Module, ModuleHelper):
    def configure(self, binder):
        import hcard_mock
        d = hcard_mock.MockDirectory(hcard_mock.TEST_FILE)

        binder.bind(ldaplib.LDAPService,
                    injector.InstanceProvider(d))
        binder.bind(KTrainingFunction,
                    injector.InstanceProvider(d.trainedThru))
        binder.bind(KAppSecret, 
                    injector.InstanceProvider('sekrit'))

    @classmethod
    def login_info(self, mc, cn):
        box = mc.sealer.seal((cn, mc._app_secret))
        req = MockRequest()
        return box, req

    @classmethod
    def mods(cls):
        return [Mock()]


class MockRequest(AttrDict):
    pass


class RunTime(injector.Module, ModuleHelper):
    def __init__(self, ini='integration-test.ini'):
        injector.Module.__init__(self)
        self._ini = ini

    @provides(KTrainingFunction)
    def training(self):
        return chalkdb_queryfn(self._ini, CHALK_CONFIG_SECTION)

    @classmethod
    def mods(cls, ini='integration-test.ini'):
        return [cls(ini), ldaplib.RunTime(ini)]


if __name__ == '__main__': # pragma: no cover
    import pprint

    m = RunTime.make()

    if '--search' in sys.argv:
        cn, sn, givenname = sys.argv[2:5]

        print [10, cn, sn, givenname]
        print m.affiliateSearch(10, cn, sn, givenname)
    else:
        uid = sys.argv[1]
        box, req = Mock.login_info(m, uid)
        m.issue(box, req)
        who = m.read_badge(req.idvault_entry)
        print who
        print "training: ", m.training(req.idvault_entry)
