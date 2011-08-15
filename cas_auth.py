'''cas_auth - JA-SIG Central Authentication Service (CAS_) support

.. _CAS: http://www.jasig.org/cas

'''

import uuid
from cgi import parse_qs, escape
from urlparse import urljoin
from urllib import urlencode

from paste.httpexceptions import HTTPSeeOther, HTTPForbidden
from beaker.middleware import SessionMiddleware
from paste.auth.cas import AuthCASHandler
from paste.request import parse_querystring, construct_url

def cas_required(cas, session_key, router, app_login, app_logout, app):
    '''Wrap an app in a CAS-authenticated session.
    @param cas: base address of CAS service
    @param session_key: per beaker.middleware (not sure I grok)
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
        exc = HTTPSeeOther(app_login)
        return exc.wsgi_application(environ, start_response)

    def handle_logout(environ, start_response):
        if environ['REQUEST_METHOD'] == 'POST':
            session = environ['beaker.session']
            session.invalidate()
            session.save()
            exc = HTTPSeeOther(urljoin(cas, 'logout'))
            return exc.wsgi_application(environ, start_response)
        else:
            return HTTPForbidden().wsgi_application(environ, start_response)

    session_opts = make_session(session_key)
    wrap_login = SessionMiddleware(login_to_session, session_opts)
    wrap_logout = SessionMiddleware(handle_logout,  session_opts)
    wrap_app = SessionMiddleware(require_userid,  session_opts)
    return router(app_login, AuthCASHandler(wrap_login, cas),
                  router(app_logout, wrap_logout, wrap_app))


def make_session(k):
    session_secret = str(uuid.uuid4())
    session_opts = {
        #<benbangert> non-cookie based sessions use secret, cookie-based use validatE_key instead
        #<benbangert> should prolly clarify that
        'session.secret': session_secret,
        'session.validate_key': session_secret,
        
        'session.type': 'cookie',
        'session.key': k,  # umm... not sure I grok this.
        'session.auto': True,
        #@@ secure
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
            
