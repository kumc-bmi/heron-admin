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
