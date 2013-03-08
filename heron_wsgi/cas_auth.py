r'''cas_auth - JA-SIG Central Authentication Service (CAS_) support

.. _CAS: http://www.jasig.org/cas

Suppose we have a `pyramid view`__ that we want protected by CAS.

__ http://docs.pylonsproject.org/projects/pyramid/en/1.2-branch/narr/views.html

Setup: Pyramid Configuration, Paste TestApp
===========================================

  >>> from pyramid.config import Configurator
  >>> config = Configurator()

Building a pyramid authorization policy using the cas_auth.Validator
====================================================================

Let's set up authorization and authentication, starting
with a Validator and a mock Issuer and config::

  >>> guard, guide, rt = Mock.make([Validator,
  ...                               Issuer, (Options, CONFIG_SECTION)])


  >>> CapabilityStyle.setup(config, rt.app_secret, 'logout', 'logout',
  ...                       guide.authenticated, [guide], guard)

Note the CAS base URI from the configuration options::

  >>> rt.base
  'http://example/cas/'

And finally, we can add a view, using the guide's permission::

  >>> config.add_route('root', '')
  >>> config.add_view(MockIssuer.protected_view, route_name='root',
  ...                 permission=guide.permission)


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

TODO: detect clients that refused the cookie.

Now, our protected app runs inside an `auth_tkt` session::

  >>> r4 = r3.follow(status=200)
  >>> r4
  <Response 200 OK 'john.smith found: se'>
  >>> [v.split('=', 1)[0] for (n, v) in r3.headers
  ...  if n.lower() == 'set-cookie']
  ['auth_tkt', 'auth_tkt']


Session Expiration
==================

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

from admin_lib.rtconfig import (Options, TestTimeOptions, RuntimeOptions,
                                IniModule)
from admin_lib.rtconfig import MockMixin
from admin_lib.ocap_file import edef, Token
from admin_lib.ocap_file import WebReadable

log = logging.getLogger(__name__)

CONFIG_SECTION = 'cas'


class Issuer(Token):
    '''Issuer of capabilities based on CAS login credentials.

    See MockIssuer for an example.
    '''
    permissions = ()

    def __repr__(self):
        return self.__class__.__name__ + '()'

    def authenticated(self, uid, req):
        '''Mark a request's context as authenticated.

        @param req: request, whose context you should add a `remote_user`
                    capability to, for use in grant().
        @return: a sequence of pyramid principals, which should be empty,
                 since this is not ACL style.
        '''
        raise NotImplementedError  # pragma: nocover

    def grant(self, context, permission):
        '''Grant capabilities relevant to a permission.

        @param context: request context, which should be
                        tested to ensure that it is authenticated as above.
        @param permission: permission desired by a view
        @raises: TypeError if permission is not permitted in this context.
        '''
        raise NotImplementedError  # pragma: nocover


class Validator(Token):
    @inject(cascap=(WebReadable, CONFIG_SECTION))
    def __init__(self, cascap):
        '''
        :param cas_rd: capability to read `/validate`, `/logout` etc.
                       For the examples in the `CAS protocol spec`__,
                       `cas_rd.fullPath()` would be `https://server/cas/'.
        __ http://www.jasig.org/cas/protocol

        '''
        self.__cascap = cascap
        self.__authenticated = None

    def __repr__(self):
        return 'Validator(cas_addr=%s)' % self.__cascap.fullPath()

    def introduce(self, authenticated):
        '''Introduce Validator to authentication callback.

        :param authenticated: a callable with (uid, request)
                              args. This is called when a request
                              bears an authentic session cookie that
                              was created on presentation of a valid
                              CAS ticket.

        '''
        self.__ok = authenticated

    def configure(self, config, logout_route, secret,
                  timeout=10 * 60,
                  reissue_time=1 * 60):
        '''Apply configuration hooks:

        1. an authentication policy
        2. checkTicket NewRequest event handler
        3. redirect-to-CAS-service view
        4. logout view
        5. session factory

        >>> raise NotImplementedError('encrypted session factory for CSRF')
        '''
        clearsigned = UnencryptedCookieSessionFactoryConfig(secret)
        config.set_session_factory(clearsigned)

        assert self.__ok

        config.set_authentication_policy(AuthTktAuthenticationPolicy(
                secret, callback=self.__ok,
                timeout=timeout,
                reissue_time=reissue_time,
                wild_domain=False))

        config.add_subscriber(self.checkTicket, pyramid.events.NewRequest)

        config.add_view(self.redirect,
                        context=pyramid.exceptions.HTTPForbidden,
                        permission=pyramid.security.NO_PERMISSION_REQUIRED)

        config.add_view(self.logout, route_name=logout_route,
                        request_method='POST')

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

    def logout(self, context, req):
        req.session.invalidate()
        there = self.__cascap.subRdFile('logout')
        response = HTTPSeeOther(there.fullPath())
        response.headers.extend(security.forget(req))
        log.info('dropping session cookie and redirecting to %s', there)
        raise response


class CapabilityStyle(object):
    '''An object-capability style pyramid authorization policy.

    Given a list of issuers, when asked to grant a permission in a
    context, we ask each of the issuers to grant capabilities for the
    given permission in that context.

    '''

    @classmethod
    def setup(cls, config, secret, logout_route, logout_path,
              authenticated, issuers, validator):
        '''Set up capability style authorization policy.

        1. Introduce the validator to the authenticated callback.
        so that the guard will delegate authentic requests to the guide.

        2. Set up logout view

        3. Configure the validator.

        4. Set config authorization policy based on issuers.
        '''
        validator.introduce(authenticated)
        config.add_route(logout_route, logout_path)
        validator.configure(config, logout_route, secret)
        config.set_authorization_policy(cls(issuers))

    def __init__(self, issuers):
        self.__issuers = issuers

    def permits(self, context, principals, permission):
        '''Ask each issuer to grant capabilities for this permission.

        @return: True iff an audit raised no exception.
        '''
        for issuer in self.__issuers:
            try:
                issuer.grant(context, permission)
                log.info('%s permits %s', issuer, permission)
                return True
            except TypeError:
                pass

        log.info('CapabilityStyle.permits: %s do not have %s permission.',
                 principals, permission)
        return False

    def principals_allowed_by_permission(self, context, permission):
        raise NotImplementedError  # pragma: nocover


class RunTime(IniModule):  # pragma: nocover
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

    @classmethod
    def mods(cls):
        return [Mock()]


class MockIssuer(Issuer):  # pragma: nocover
    permission = 'treasure_map'

    def __init__(self):
        from admin_lib import sealing
        self.__sealer, self.__unsealer = sealing.makeBrandPair(
            self.__class__.__name__)

    def authenticated(self, uid, req):
        cred = self.__sealer.seal(uid)
        req.context.remote_user = cred
        return []

    def grant(self, context, permission):
        log.debug('MockIssuer.grant(%s, %s)', context, permission)
        if permission is not self.permission:
            raise TypeError

        try:
            box = context.remote_user
        except AttributeError:
            raise TypeError
        else:
            who = self.__unsealer.unseal(box)  # raises TypeError
            context.treasure_map = TreasureMap(who, 'sekret place')

    @classmethod
    def protected_view(cls, context, req):
        from pyramid.response import Response
        m = req.context.treasure_map
        log.debug('protected view: %s', [m.hunter(), ' found: ',
                                         m.location()])
        return Response(app_iter=[m.hunter(),
                                  ' found: ', m.location()])


def TreasureMap(who, sekret):  # pragma: nocover
    def hunter():
        return who

    def location():
        return sekret

    def __repr__(self):
        return 'TreasureMap()'

    return edef(hunter, location, __repr__)


def _integration_test(ini, host='127.0.0.1', port=8123):  # pragma: nocover
    from pyramid.config import Configurator
    from paste import httpserver

    #logging.basicConfig(level=logging.DEBUG)
    logging.basicConfig(level=logging.INFO)

    config = Configurator(settings={'pyramid.debug_routematch': True})

    guide, guard, rt = RunTime.make(
        ini, [MockIssuer, Validator, (Options, CONFIG_SECTION)])

    CapabilityStyle.setup(config, rt.app_secret, 'logout', 'logout',
                          guide.authenticated, [guide], guard)

    config.add_route('root', '')
    config.add_view(MockIssuer.protected_view, route_name='root',
                    permission=guide.permission)

    app = config.make_wsgi_app()
    httpserver.serve(app, host, port)


if __name__ == '__main__':  # pragma: nocover
    import sys
    ini = sys.argv[1]
    _integration_test(ini)
