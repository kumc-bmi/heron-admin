'''medcenter.py -- academic medical center directory/policy

  # logging.basicConfig(level=logging.DEBUG)
  >>> m, mock, mods, depgraph = Mock.make_stuff()
  >>> app_secret = depgraph.get(KAppSecret)

Assuming CAS login asked us to issue a login capability::

  >>> box, req = mock.login_info('john.smith')
  >>> login_caps = m.issue(box, req)

We can exercise an enterprise directory capability::

  >>> a1 = req.idvault_entry
  >>> m.withId(a1, lambda a: '%s %s <%s>' % (
  ...                         a['givenname'], a['sn'], a['mail']))
  'John Smith <john.smith@js.example>'
  >>> m.withId(a1, lambda a: a['title'])
  'Chair of Department of Neurology'

Note: KUMC uses ou for department. @@test

We use an outboard service to check human subjects "chalk" training::

  >>> print _sample_chalk_settings.inifmt(CHALK_CONFIG_SECTION)
  [chalk]
  param=userid
  url=http://localhost:8080/chalk-checker

  >>> m.training(a1)
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
        matches = self._svc.search('(cn=%s)' % name, AccountHolder.attributes)
        if len(matches) != 1:
            if len(matches) == 0:
                raise KeyError, name
            else: # pragma nocover
                raise ValueError, name  # ambiguous

        dn, ldapattrs = matches[0]
        return AccountHolder.rezip(ldapattrs)

    def issue(self, loginbox, req):
        u, s = self._unsealer.unseal(loginbox)
        if s != self._app_secret:
            log.warn('expected app_secret [%s] got [%s]',
                     self._app_secret, s)
            return []
        cap = self.sealer.seal(self._lookup(u))
        req.idvault_entry = cap
        return [cap]

    def audit(self, cap, p):
        log.info('MedCenter.audit(%s, %s)' % (cap, p))
        if not isinstance(cap, object):
            raise TypeError
        self._unsealer.unseal(cap)

    def lookup(self, namebox):
        name = self._unsealer.unseal(namebox)
        return self.sealer.seal(self._lookup(name))

    def withId(self, attrsbox, thunk):
        '''Exercise thunk(attrs) provided attrsbox unseals.
        '''
        attrs = self._unsealer.unseal(attrsbox)
        return thunk(attrs)

    def withFaculty(self, attrsbox, thunk):
        '''Exercise thunk(attrs) provided attrsbox unseals as faculty.
        @raises: TypeError on unsealing failure
        @raises: NotFaculty
        '''
        attrs = self._unsealer.unseal(attrsbox)
        log.debug('withFaculty: %s', attrs)
        if (attrs['kumcPersonJobcode'] == self.excluded_jobcode
            or attrs['kumcPersonFaculty'] != 'Y'):
            raise NotFaculty

        return thunk(attrs)

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

        results = self._svc.search(q, AccountHolder.attributes)[:max_qty]
        return [AccountHolder.rezip(ldapattrs)
                for dn, ldapattrs in results]


def _extract_values(attrs):
    return [attrs.get(n, [None])[0]
            for n in AccountHolder.attributes]


class NotFaculty(Exception):
    pass


class AccountHolder(object):
    '''
    Note: KUMC uses ou for department.
    '''
    attributes = ["cn", "ou", "sn", "givenname", "title", "mail",
                  "kumcPersonFaculty", "kumcPersonJobcode"]

    @classmethod
    def rezip(cls, ldapattrs):
        return dict(zip(cls.attributes, _extract_values(ldapattrs)))

    def __init__(self, cap, attrs):
        self.cap = cap
        self._attrs = attrs

    def __str__(self):
        return '%s %s <%s>' % (self.givenname, self.sn, self.mail)

    def __repr__(self):
        return str(self)

    def userid(self):
        # TODO: use python property stuff?
        return self.cn

    def __getattr__(self, n):
        if n.startswith('_') or n not in self.attributes:
            raise AttributeError
        return self._attrs[n]


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


class Mock(injector.Module):
    def configure(self, binder):
        import hcard_mock
        d = hcard_mock.MockDirectory(hcard_mock.TEST_FILE)

        binder.bind(ldaplib.LDAPService,
                    injector.InstanceProvider(d))
        binder.bind(KTrainingFunction,
                    injector.InstanceProvider(d.trainedThru))
        self._app_secret = 'sekrit'
        binder.bind(KAppSecret, 
                    injector.InstanceProvider(self._app_secret))

    def set_medcenter(self, mc):
        self._mc = mc

    def login_info(self, cn):
        box = self._mc.sealer.seal((cn, self._app_secret))
        req = MockRequest()
        return box, req

    @classmethod
    def mods(cls):
        return [Mock()]

    @classmethod
    def make_stuff(cls):
        mods = cls.mods()
        mod = mods[-1]
        depgraph = injector.Injector(mods)
        mc = depgraph.get(MedCenter)
        mod.set_medcenter(mc)
        return mc, mod, mods, depgraph


class MockRequest(dict):
    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        self.__dict__ = self

class IntegrationTest(injector.Module):
    def __init__(self, ini='integration-test.ini'):
        injector.Module.__init__(self)
        self._ini = ini

    @provides(KTrainingFunction)
    def training(self):
        return chalkdb_queryfn(self._ini, CHALK_CONFIG_SECTION)

    @classmethod
    def deps(cls):
        return [IntegrationTest, ldaplib.IntegrationTest]

    @classmethod
    def depgraph(cls):
        return injector.Injector([class_() for class_ in cls.deps()])


if __name__ == '__main__': # pragma: no cover
    import pprint

    depgraph = IntegrationTest.depgraph()
    m = depgraph.get(MedCenter)

    if '--search' in sys.argv:
        cn, sn, givenname = sys.argv[2:5]

        print [10, cn, sn, givenname]
        print m.affiliateSearch(10, cn, sn, givenname)
    else:
        uid = sys.argv[1]
        who = m.affiliate(uid)
        print who
        print "training: ", m.trainedThru(who)
