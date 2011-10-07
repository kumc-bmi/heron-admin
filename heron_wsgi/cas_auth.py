'''cas_auth - JA-SIG Central Authentication Service (CAS_) support

.. _CAS: http://www.jasig.org/cas

Suppose we have an app that we want protected by CAS::
  >>> def protected(environ, start_response):
  ...     session = environ['beaker.session']
  ...     u = session['user']
  ...     start_response('200 OK', [('content-type', 'text/plain')])
  ...     return ['logged in user:', u]

Let's wrap it in `cas_required`::
  >>> import urllib
  >>> addr = 'http://example/cas/'
  >>> session_opts = make_session('ex', uuid_maker=lambda: '1234-5678')
  >>> cr = cas_required(addr, session_opts, prefix_router, '/login', '/logout', protected)

An initial visit to the root page redirects to the login path and sets a cookie::
  >>> from paste.fixture import TestApp
  >>> t = TestApp(cr)
  >>> r1 = t.get('/', status=303)
  >>> def _loc(headers):
  ...    return [v for (n, v) in headers if n.lower() == 'location'][0]
  >>> _loc(r1.headers)
  '/login'
  >>> ['Found cookie' for (n, v) in r1.headers if n.lower() == 'set-cookie']
  ['Found cookie']

The next step is a link to the CAS service with the `service` param set to our login address::
   >>> r2 = r1.follow()
   >>> _loc(r2.headers)
   'http://example/cas/login?service=http%3A%2F%2Flocalhost%2Flogin'

The the CAS service redirects back with a ticket::

   >>> with default_urlopener(LinesUrlOpener(['yes', 'john.smith'])):
   ...     r3 = t.get('/login?ticket=ST-381409-fsFVbSPrkoD9nANruV4B-example', status=303)
   >>> _loc(r3.headers)
   'http://localhost/'

And finally, our protected app runs:
   >>> r3.follow(status=200)
   <Response 200 OK 'logged in user:john.'>
'''

import uuid
from cgi import parse_qs, escape
from urlparse import urljoin
from urllib import urlencode
from contextlib import contextmanager
import urllib

from paste.httpexceptions import HTTPSeeOther, HTTPForbidden
from beaker.middleware import SessionMiddleware
from paste.auth.cas import AuthCASHandler
from paste.request import parse_querystring, construct_url

def cas_required(cas, session_opts, router, app_login, app_logout, app):
    '''Wrap an app in a CAS-authenticated session.
    @param cas: base address of CAS service
    @param session_opts: per beaker.middleware (not sure I grok)
    @param router: a thunk(addr, app_for_addr, app_else) router func
    @param app_login: path that we will route to login resource
    @param app_logout: path that we will route to logout resource
    @app: app that will only be called inside a CAS-protected session.
    '''
    def require_userid(environ, start_response):
        session = environ['beaker.session']
        if 'user' in session:
            #print "require_userid: ", session['user']
            return app(environ, start_response)
        here = construct_url(environ)
        session['here'] = here
        #print "script name: ", environ['SCRIPT_NAME']
        exc = HTTPSeeOther(environ['SCRIPT_NAME'] + app_login)
        return exc.wsgi_application(environ, start_response)

    def handle_logout(environ, start_response):
        if environ['REQUEST_METHOD'] == 'POST':
            session = environ['beaker.session']
            session.invalidate()
            session.save()
            there = urljoin(cas, 'logout')
            return HTTPSeeOther(there).wsgi_application(environ, start_response)
        else:
            return HTTPForbidden().wsgi_application(environ, start_response)

    wrap_login = SessionMiddleware(login_to_session, session_opts)
    wrap_logout = SessionMiddleware(handle_logout,  session_opts)
    wrap_app = SessionMiddleware(require_userid,  session_opts)
    return router(app_login, AuthCASHandler(wrap_login, cas),
                  router(app_logout, wrap_logout, wrap_app))


def make_session(k, uuid_maker=uuid.uuid4):
    '''
    @param k: key, per beaker.middleware (not sure I grok)

    .. todo: study 'secure' field of session_opts

    '''
    session_secret = str(uuid_maker())
    session_opts = {
        #<benbangert> non-cookie based sessions use secret, cookie-based use validatE_key instead
        #<benbangert> should prolly clarify that
        'session.secret': session_secret,
        'session.validate_key': session_secret,
        
        'session.type': 'cookie',
        'session.key': k,  # umm... not sure I grok this.
        'session.auto': True,
        }
    return session_opts


def login_to_session(environ, start_response):
    '''Capture CAS user in session variable and redirect to session['here']

    Route /your/login/address to this.
    '''
    session = environ['beaker.session']
    session['user'] = environ['REMOTE_USER']
    next = session['here']
    exc = HTTPSeeOther(next)
    return exc.wsgi_application(environ, start_response)
            

def route_if_prefix(prefix, app_match, app_else, environ, start_response):
    path = environ['PATH_INFO']
    if path.startswith(prefix):
        return app_match(environ, start_response)
    else:
        return app_else(environ, start_response)


def prefix_router(prefix, app_match, app_else):
    assert app_match is not None
    assert app_else is not None
    def handle_request(environ, start_response):
        return route_if_prefix(prefix, app_match, app_else, environ, start_response)
    return handle_request

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


@contextmanager
def default_urlopener(u):
    '''Override URLOpener used in urllib.urlopen(), e.g. by paste.auth.cas
    '''
    sv = urllib._urlopener
    urllib._urlopener = u
    try:
        yield None
    finally:
        urllib._urlopener = sv










# python stdlib 1st, per PEP8
import urllib
import urllib2
import logging

# from pypi
import injector
from injector import inject, provides

import pyramid
from pyramid import security
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPUnauthorized, HTTPBadRequest
from pyramid.httpexceptions import HTTPForbidden, HTTPFound
from pyramid.events import NewRequest
from pyramid.events import subscriber
from pyramid.authentication import CallbackAuthenticationPolicy
from pyramid.authentication import AuthTktAuthenticationPolicy

from admin_lib.config import Options, TestTimeOptions

log = logging.getLogger(__name__)

CONFIG_SECTION='cas'
PERMISSION='enterprise'

class Redirector(object):
    def __init__(self, cas_addr):
        self._a = cas_addr

    def configure(self, config):
        config.add_view(self,
                        context=pyramid.exceptions.HTTPForbidden,
                        permission=pyramid.security.NO_PERMISSION_REQUIRED)

    def __call__(self, context, request):
        import sys
        if 'ticket' in request.params:
            # already been here before
            raise HTTPForbidden

        log.debug("redirector from: %s", request.url)
        there = (urllib.basejoin(self._a, 'login') + '?' +
                 urllib.urlencode(dict(service=request.url)))
        log.debug("redirector to: %s, %s, %s", there, self._a, request.url)
        return HTTPFound(there)


class Validator(object):
    def __init__(self, cas_addr, ua=None):
        if ua is None:
            ua = urllib2.build_opener()
        self._ua = ua
        self._a = cas_addr

    def __str__(self):
        return 'Validator(cas_addr=%s)' % self._a

    def policy(self, app_secret):
        return AuthTktAuthenticationPolicy(
            app_secret, callback=self.cap)    
        
    def configure(self, config):
        config.add_subscriber(self.check, pyramid.events.NewRequest)

    def check(self, event):
        req = event.request

        log.debug('check %s', req.url)

        t = req.GET.get('ticket')
        if not t:
            log.debug('no ticket arg')
            return None  # or: raise HTTPBadRequest()

        a = self._a + 'validate?' + urllib.urlencode(dict(service=req.path_url,
                                                          ticket=t))
        log.debug('cas validation request: %s', a)
        lines = self._ua.open(a).read().split('\n')

        log.debug('cas validation result: %s', lines)

        if not(lines and lines[0] == 'yes'):
            return None  # or: raise HTTPForbidden()

        uid = lines[1].strip()

        hdrs = security.remember(req, uid)
        log.debug("new headers: %s", hdrs)

        response = HTTPFound(req.path_url)
        response.headers.extend(hdrs)
        raise response

    def cap(self, uid, req):
        import sys
        log.debug('cap: %s %s', uid, req)
        def cap():
            return (self, uid)

        req.remote_user = uid
        req.login_cap = cap
        return [cap]
        
    def audit(self, cap):
        '''unsealer, sorta

        @raises TypeError on audit failure
        '''
        x, u = cap()
        if x is not self:
            raise TypeError
        return u


class SetUp(injector.Module):
    @provides(CallbackAuthenticationPolicy)
    @inject(guard=Validator,
            rt=(Options, CONFIG_SECTION))
    def policy(self, guard, rt):
        log.debug('making policy from %s, %s', rt.app_secret, guard)
        return AuthTktAuthenticationPolicy(
            rt.app_secret, callback=guard.cap)    
        
    @provides(Validator)
    @inject(rt=(Options, CONFIG_SECTION),
            ua=urllib.URLopener)
    def validator(self, rt, ua):
        return Validator(rt.base, ua)
        
    @provides(Redirector)
    @inject(rt=(Options, CONFIG_SECTION))
    def redirector(self, rt):
        return Redirector(rt.base)


class TestTime(injector.Module):
    def __init__(self, base):
        self._base = base

    def configure(self, binder):
        binder.bind((Options, CONFIG_SECTION),
                    to=TestTimeOptions({'base': self._base,
                                        'app_secret': 'sekrit'}))
        binder.bind(urllib.URLopener,
                    to=injector.InstanceProvider(urllib2.build_opener()))

    @classmethod
    def depgraph(cls):
        return injector.Injector([SetUp(), Mock()])


class Mock(injector.Module):
    def configure(self, binder):
        binder.bind((Options, CONFIG_SECTION),
                    to=TestTimeOptions({'base': 'http://example/cas/',
                                        'app_secret': 'sekrit'}))
        binder.bind(urllib.URLopener,
                    to=injector.InstanceProvider(LinesUrlOpener(
                    ['yes', 'john.smith'])))

    @classmethod
    def depgraph(cls):
        return injector.Injector([SetUp(), Mock()])


class _TestAuthz(object):
    def permits(self, context, principals, permission):
        log.debug('permits? %s %s %s', context, principals, permission)
        if permission == PERMISSION:
            return 'system.Authenticated' in principals

        return True

    def principals_allowed_by_permission(self, context, permission):
        raise NotImplementedError


def _integration_test(cas_base, host='127.0.0.1', port=8123):
    from pyramid.config import Configurator
    from pyramid.response import Response
    from paste import httpserver

    logging.basicConfig(level=logging.DEBUG)

    def protected_view(req):
        return Response(app_iter=['I am: ', req.remote_user])

    depgraph = injector.Injector([TestTime(cas_base), SetUp()])
    val = depgraph.get(Validator)
    rt = depgraph.get((Options, CONFIG_SECTION))
    config = Configurator(settings={'pyramid.debug_routematch': True},
                          authentication_policy=val.policy(rt.app_secret),
                          authorization_policy=_TestAuthz(),
                          default_permission=PERMISSION
                          )

    rd = depgraph.get(Redirector)

    val.configure(config)
    rd.configure(config)

    config.add_route('root', '')
    config.add_view(protected_view, route_name='root')

    app = config.make_wsgi_app()
    httpserver.serve(app, host, port)


if __name__ == '__main__':
    import sys
    cas_base = sys.argv[1]
    _integration_test(cas_base)

