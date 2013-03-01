r'''cas_auth - JA-SIG Central Authentication Service (CAS_) support

.. _CAS: http://www.jasig.org/cas

Suppose we have a `pyramid view`__ that we want protected by CAS.

__ http://docs.pylonsproject.org/projects/pyramid/en/1.2-branch/narr/views.html

Setup: Pyramid Configuration, Paste TestApp
===========================================

  >>> from pyramid.config import Configurator
  >>> config = Configurator()

A Simple Protected View
=======================

  >>> from pyramid.response import Response
  >>> def protected_view(context, req):
  ...     log.debug('protected view: %s', ['found it: ',
  ...                                      req.treasure_map.location()])
  ...     return Response(app_iter=['found it: ', req.treasure_map.location()])


Building a pyramid authorization policy using the cas_auth.Validator
====================================================================

Let's set up authorization and authentication, starting
with a Validator and a mock Issuer and config::

  >>> guard, guide, rt = Mock.make([Validator,
  ...                               Issuer, (Options, CONFIG_SECTION)])

Note the CAS base URI from the configuration options::

  >>> rt.base
  'http://example/cas/'

The guard supplies a logout view, attached to the route we specify::

  >>> config.add_route('logout', 'logout')
  >>> guard.configure(config, 'logout')

We must introduce the guide (Issuer) to the guard (Validator)
so that the guard will accept capabilities from the guide::

  >>> guard.add_issuer(guide)

Now we can set the authorization policy to use capabilities
from the guide::

  >>> config.set_authorization_policy(CapabilityStyle([guide]))

And finally, we can add our view, using the guide's permission::

  >>> config.add_route('root', '')
  >>> config.add_view(protected_view, route_name='root',
  ...                 permission=guide.permissions[0])


Now we can make a WSGI application from our configuration::

  >>> from paste.fixture import TestApp
  >>> t = TestApp(config.make_wsgi_app())

CAS Login Protocol Walkthrough
==============================

An initial visit redirects to the CAS service with the `service` param
set to our login address::

  >>> r1 = t.get('/', status=303)
  >>> def _loc(headers):
  ...    return [v for (n, v) in headers if n.lower() == 'location'][0]
  >>> _loc(r1.headers)
  'http://example/cas/login?service=http%3A%2F%2Flocalhost%2F'

The the CAS service redirects back with a ticket::

  >>> r3 = t.get('/?ticket=ST-381409-fsFVbSPrkoD9nANruV4B-example',
  ...            status=302)
  >>> _loc(r3.headers)
  'http://localhost/'

Now, our protected app runs inside an `auth_tkt` session::

  >>> r4 = r3.follow(status=200)
  >>> r4
  <Response 200 OK 'found it: Canary Isl'>
  >>> [v.split('=', 1)[0] for (n, v) in r3.headers
  ...  if n.lower() == 'set-cookie']
  ['auth_tkt', 'auth_tkt']

Then, more than 10 minutes later, the session has timed out,
so we should get a challenge on the next request::

  >>> from pyramid.authentication import AuthTktCookieHelper
  >>> import time
  >>> AuthTktCookieHelper.now = time.time() + 40 * 60

  >>> _loc(t.get(r4.request.url, status=303).headers)
  'http://example/cas/login?service=http%3A%2F%2Flocalhost%2F'

Finally, log in again and log out, and then get a challenge::

  >>> rlogin2 = t.get('/?ticket=ST-381409-fsFVbSPrkoD9nANruV4B-example',
  ...                 status=302)
  >>> rlogout = t.post('/logout', status=303)
  >>> _loc(rlogout.headers)
  'http://example/cas/logout'

  >>> r0 = t.get('/', status=303)
  >>> _loc(r0.headers)
  'http://example/cas/login?service=http%3A%2F%2Flocalhost%2F'
'''

# python stdlib 1st, per PEP8
import itertools
import logging
from urllib import urlencode

# from pypi
import injector
from injector import inject, provides

import pyramid
from pyramid import security
from pyramid.httpexceptions import HTTPForbidden, HTTPFound, HTTPSeeOther
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.session import UnencryptedCookieSessionFactoryConfig

from admin_lib.rtconfig import Options, TestTimeOptions, RuntimeOptions
from admin_lib.rtconfig import MockMixin
from admin_lib import notary
from admin_lib.ocap_file import edef
from admin_lib.ocap_file import WebReadable

log = logging.getLogger(__name__)

CONFIG_SECTION = 'cas'


class Issuer(object):
    '''Issuer of capabilities based on CAS login credentials.

    See MockIssuer for an example.
    '''
    permissions = ()

    def issue(self, uid, req):
        '''Issue capabilities based on CAS login.

        @param req: request, bearing CAS userid in remote_user,
                    which you may add capability attributes to
        @return: a sequence of authorizations for this capabilities
                 added to this request, which will later be passed to
                 audit in case this issuer's permission is required.
        '''
        raise NotImplementedError  # pragma: nocover

    def audit(self, cap, permission):
        '''Test whether cap authorizes permission.

        @param cap: any object, which should be tested to see if it is
                    an authorization we issued.
        @param permission: one of this issuer's permissions
        @raises: TypeError if cap is not one we issued for permission.
        '''
        raise NotImplementedError  # pragma: nocover


class Validator(object):
    @inject(cascap=(WebReadable, CONFIG_SECTION),
            rt=(Options, CONFIG_SECTION))
    def __init__(self, cascap, rt):
        self.__cascap = cascap
        # When this thing is missing from the config file,
        # the stacktrace is really obscure.
        assert rt.app_secret
        self.__secret = rt.app_secret
        self._issuers = []

    def __str__(self):
        return 'Validator(cas_addr=%s)' % self._webrdcap.fullPath()

    def configure(self, config, logout_route,
                  timeout=10 * 60,
                  reissue_time=1 * 60):
        '''Apply configuration hooks:

        1. an authentication policy
        2. checkTicket NewRequest event handler
        3. redirect-to-CAS-service view
        4. logout view
        5. session factory
        '''
        clearsigned = UnencryptedCookieSessionFactoryConfig(self.__secret)
        config.set_session_factory(clearsigned)

        config.set_authentication_policy(AuthTktAuthenticationPolicy(
                self.__secret, callback=self.issue_caps,
                timeout=timeout,
                reissue_time=reissue_time,
                wild_domain=False))

        config.add_subscriber(self.checkTicket, pyramid.events.NewRequest)

        config.add_view(self.redirect,
                        context=pyramid.exceptions.HTTPForbidden,
                        permission=pyramid.security.NO_PERMISSION_REQUIRED)

        config.add_view(self.logout, route_name=logout_route,
                        request_method='POST')

    def add_issuer(self, issuer):
        self._issuers.append(issuer)

    def checkTicket(self, event):
        '''Check ticket of new request.

        This is used as a NewRequest event handler. See module
        documentation for the normal protocol sequence.

        @raises: HTTPFound() with a redirection to clean up the query
                 part of the URL, if CAS validation succeeds (r3 in
                 protocol walkthrough above).

        @returns: None if there is no ticket parameter in the event
                  request URL query, which indicates either
                  (1) a new session (r1 above), in which case pyramid should
                  call our redirect view, or
                  (2) an existing, authenticated session
                  (3) a failed CAS verification. (untested?!)
        '''
        req = event.request

        t = req.GET.get('ticket')
        if not t:
            log.info('checkTicket at %s: no ticket to check.', req.url)
            return None

        valcap = self.__cascap.subRdFile('validate?' + urlencode(
            dict(service=req.path_url, ticket=t)))

        log.info('checkTicket for <%s>: cas validation request: %s',
                 req.url, valcap.fullPath())
        lines = valcap.getBytes().split('\n')

        if not(lines and lines[0] == 'yes'):
            log.info('cas validation failed: %s', lines)
            return None  # or: raise HTTPForbidden()

        uid = lines[1].strip()

        hdrs = security.remember(req, uid)
        #log.debug("new headers: %s", hdrs)

        response = HTTPFound(req.path_url)
        response.headers.extend(hdrs)
        log.info('cas validation succeeded for: %s '
                 'redirecting to %s with session cookie',
                 uid, req.path_url)
        raise response

    def redirect(self, context, request):
        '''Redirect to CAS service with service=... return pointer.

        A la r1 in protocol walkthrough above.
        '''
        if 'ticket' in request.params:
            # already been here before
            return HTTPForbidden()

        there = self.__cascap.subRdFile(
            'login?' + urlencode(dict(service=request.url)))
        log.info('Validator.redirect to %s (service=%s)',
                 there.fullPath(), request.url)
        return HTTPSeeOther(there.fullPath())

    def issue_caps(self, uid, req):
        '''AuthTktAuthenticationPolicy callback that allows each issuer
        to add capabilities to the request.
        '''
        log.debug('issuing CAS login capabilities for: %s', uid)
        return _flatten([issuer.issue(uid, req)
                         for issuer in self._issuers])

    def logout(self, context, req):
        req.session.invalidate()
        there = self.__cascap.subRdFile('logout')
        response = HTTPSeeOther(there.fullPath())
        response.headers.extend(security.forget(req))
        log.info('dropping session cookie and redirecting to %s', there)
        raise response


def _flatten(listoflists):
    return list(itertools.chain(*listoflists))


class CapabilityStyle(object):
    '''An object-capability style  pyramid authorization policy.

    Given a list of auditors, when asked if a set of principals
    are permitted some permission, we ask each of the auditors
    to audit each principal for the given permission.
    '''
    def __init__(self, auditors):
        self._auditors = auditors

    def permits(self, context, principals, permission):
        '''Ask each auditor to audit the principals for the permission.

        @return: True iff an audit raised no exception.
        '''
        for auditor in self._auditors:
            try:
                auditor.audit_all(principals, permission)
                log.info('%s permits %s', auditor, permission)
                return True
            except TypeError:
                pass

        log.info('CapabilityStyle.permits: %s do not have %s permission.',
                 principals, permission)
        return False

    def principals_allowed_by_permission(self, context, permission):
        raise NotImplementedError  # pragma: nocover


class RunTime(injector.Module):  # pragma: nocover
    def __init__(self, ini):
        self._ini = ini

    @provides((WebReadable, CONFIG_SECTION))
    @inject(rt=(Options, CONFIG_SECTION))
    def cas_server(self, rt):
        from urllib2 import build_opener, Request

        return WebReadable(rt.base, build_opener(), Request)

    @provides((Options, CONFIG_SECTION))
    def opts(self):
        return RuntimeOptions(['base', 'app_secret']).load(
            self._ini, CONFIG_SECTION)

    @classmethod
    def mods(cls, ini):
        return [RunTime(ini)]

    @classmethod
    def depgraph(cls, ini):
        return injector.Injector(cls.mods(ini))


class LinesUrlOpener(object):
    '''An URL opener to help with CAS testing
    '''
    def __init__(self, lines):
        self._lines = lines

    def open(self, addr, body=None):
        return LinesResponse(self._lines)


class LinesResponse(object):
    def __init__(self, lines):
        self._lines = lines

    def read(self):
        return '\n'.join(self._lines)


class Mock(injector.Module, MockMixin):
    def configure(self, binder):
        binder.bind((Options, CONFIG_SECTION),
                    to=TestTimeOptions({'base': 'http://example/cas/',
                                        'app_secret': 'sekrit'}))
        binder.bind(Issuer, MockIssuer)

    @provides((WebReadable, CONFIG_SECTION))
    @inject(rt=(Options, CONFIG_SECTION))
    def cas_server(self, rt):
        from urllib2 import Request
        ua = LinesUrlOpener(['yes', 'john.smith'])

        return WebReadable(rt.base, ua, Request)

    @provides(notary.makeNotary)
    def notary(self):
        return notary.makeNotary()

    @classmethod
    def mods(cls):
        return [Mock()]


class MockIssuer(object):  # pragma: nocover
    permissions = ('treasure',)

    def __str__(self):
        return self.__class__.__name__ + '()'

    @inject(notary=notary.makeNotary)
    def __init__(self, notary):
        self.__notary = notary

    def issue(self, uid, req):
        cap = TreasureMap(self.__notary, 'Canary Islands')
        req.treasure_map = cap
        log.debug('issuing caps')
        return [cap]

    def audit_all(self, caps, permission):
        log.debug('MockIssuer.audit_all(%s, %s)', caps, permission)
        if not permission in self.permissions:
            raise TypeError

        vouch = self.__notary.getInspector().vouch

        for cap in caps:
            try:
                vouch(cap)
                return
            except:  # e.g. in case of string principals
                pass
        raise TypeError


def TreasureMap(notary, sekret):  # pragma: nocover
    map_ = None  # forward reference

    def startVouch():
        notary.startVouch(map_)

    def location():
        return sekret

    def __repr__(self):
        return 'TreasureMap()'

    map_ = edef(startVouch, location, __repr__)
    return map_


def _integration_test(ini, host='127.0.0.1', port=8123):  # pragma: nocover
    from pyramid.config import Configurator
    from pyramid.response import Response
    from paste import httpserver

    #logging.basicConfig(level=logging.DEBUG)
    logging.basicConfig(level=logging.INFO)

    def protected_view(req):
        log.info('protected_view for: %s', req.remote_user)
        return Response(app_iter=['Location of the treasure is: ',
                                  req.treasure_map.location()])

    config = Configurator(settings={'pyramid.debug_routematch': True})

    depgraph = RunTime.depgraph(ini)
    guide = MockIssuer()
    guard = depgraph.get(Validator)
    guard.add_issuer(guide)
    config.add_route('logout', 'logout')
    guard.configure(config, 'logout')

    pwhat = CapabilityStyle([guide])
    config.set_authorization_policy(pwhat)

    config.add_route('root', '')
    config.add_view(protected_view, route_name='root',
                    permission=guide.permissions[0])

    app = config.make_wsgi_app()
    httpserver.serve(app, host, port)


if __name__ == '__main__':  # pragma: nocover
    import sys
    ini = sys.argv[1]
    _integration_test(ini)
