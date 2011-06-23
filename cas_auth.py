import uuid

from paste.httpexceptions import HTTPSeeOther
from beaker.middleware import SessionMiddleware
from paste.auth.cas import AuthCASHandler


def CASRequired(cas, app):
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

    return AuthCASHandler(SessionMiddleware(app, session_opts), cas)
