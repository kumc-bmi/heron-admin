import uuid

from paste.auth.cas import AuthCASHandler
from beaker.middleware import SessionMiddleware

class CASRequired(object):
    def __init__(self, cas, prefix, app, next):
        self._next = next
        self._prefix = prefix
        
        session_secret = str(uuid.uuid4())
        session_opts = {
            #<benbangert> non-cookie based sessions use secret, cookie-based use validatE_key instead
            #<benbangert> should prolly clarify that
            'session.secret': session_secret,
            'session.validate_key': session_secret,

            'session.type': 'cookie',
            'session.key': 'raven', # umm... not sure I grok this.
            'session.auto': True,
            #@@ secure
            }

        self._app = AuthCASHandler(SessionMiddleware(app, session_opts), cas)

    def __call__(self, environ, start_response):
        path = environ['PATH_INFO']

        if path.startswith(self._prefix):
            return self._app(environ, start_response)
        else:
            return self._next(environ, start_response)

