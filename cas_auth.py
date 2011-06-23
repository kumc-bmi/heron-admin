import uuid

from paste.httpexceptions import HTTPSeeOther, HTTPForbidden
from beaker.middleware import SessionMiddleware
from paste.auth.cas import AuthCASHandler


def cas_required(cas, app):
    session_secret = str(uuid.uuid4())
    session_opts = {
        #<benbangert> non-cookie based sessions use secret, cookie-based use validatE_key instead
        #<benbangert> should prolly clarify that
        'session.secret': session_secret,
        'session.validate_key': session_secret,
        
        'session.type': 'cookie',
        'session.key': 'raven',  # umm... not sure I grok this.
        'session.auto': True,
        #@@ secure
        }

    app = AuthCASHandler(SessionMiddleware(app, session_opts), cas)
    return app, session_opts


def logout(cas_logout, session_opts):
    l = _Logout(cas_logout)
    return SessionMiddleware(l, session_opts)

class _Logout(object):
    '''Invalidate the session and redirect to CAS logout page.

    Must be wrapped in :class:`beaker.session.SessionMiddleWare`.
    '''
    def __init__(self, cas_logout):
        self._logout = cas_logout

    def __call__(self, environ, start_response):
        if environ['REQUEST_METHOD'] == 'POST':
            session = environ['beaker.session']
            session.invalidate()
            session.save()
            exc = HTTPSeeOther(self._logout)
            return exc.wsgi_application(environ, start_response)
        else:
            return HTTPForbidden().wsgi_application(environ, start_response)
            
