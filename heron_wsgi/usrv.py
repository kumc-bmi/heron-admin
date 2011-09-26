'''usrv.py -- a micro web server for genshi-based site dev

'''

# stdlib imports 1st per
# PEP 8 -- Style Guide for Python Code
# http://www.python.org/dev/peps/pep-0008/
import os
import wsgiref.util as wsgi

# from PyPI - the Python Package Index http://pypi.python.org/pypi
from genshi.template import MarkupTemplate, TemplateLoader, TemplateNotFound
from beaker.middleware import SessionMiddleware

# see http://code.google.com/p/modwsgi/wiki/VirtualEnvironments 
import site
from os.path import join, dirname
site.addsitedir(dirname(__file__))

import cas_auth
from cas_auth import prefix_router, route_if_prefix

HTMLu = 'text/html; charset=utf-8'


class TemplateApp(object):
    def __init__(self, partsfn, docroot=None):
        if docroot is None:
            docroot = 'htdocs'
        docroot = os.path.join(dirname(__file__), docroot)
        self._docroot = docroot
        self._loader = TemplateLoader([docroot], auto_reload=True)
        self._partsfn = partsfn

    def __call__(self, environ, start_response):
        path = environ['PATH_INFO']
        session = environ['beaker.session']

        if path == '/':
            path = '/index.html'

        # url-decode path?
        try:
            tmpl = self._loader.load(path[1:])
            parts = self._partsfn(environ, session)
            #print >> sys.stderr, "TemplateApp parts:", pprint.pformat(parts)
            stream = tmpl.generate(**parts)
            body = stream.render('xhtml')
        except TemplateNotFound as e:
            start_response("404 not found", [('Content-type', 'text/plain')])
            #print ['docroot: ', self._docroot, '  ', str(e)]
            return 'We have no page at that address. Broken link? Typo?'

        start_response("200 ok", [('Content-type', HTMLu)])
        return [body]


def raven_parts(environ, session):
    raven_home = wsgi.application_uri(environ)
    if not raven_home.endswith('/'):
        raven_home = raven_home + '/'
    return dict(user=session.get('user', ""),
                raven_home=raven_home)


def _mkapp(cas='https://cas.kumc.edu/cas/', auth_area='/u/',
           login='/u/login', logout='/u/logout'):
    '''
    .. todo: consider removing this dead code
    '''
    session_opts = cas_auth.make_session('raven')
    t = SessionMiddleware(TemplateApp(raven_parts), session_opts)
    return prefix_router(auth_area,
                         cas_auth.cas_required(cas, session_opts, prefix_router,
                                               login, logout, t), t)

# mod_wsgi conventional entry point
application = _mkapp()


if __name__ == '__main__':
    # test usage
    from paste import httpserver
    from paste import fileapp
    import sys
    host, port = sys.argv[1:3]

    # In production use, static A/V media files would be
    # served with apache, but for test purposes, we'll use
    # paste DirectoryApp
    app = prefix_router('/av/', fileapp.DirectoryApp('htdocs/'), application)

    httpserver.serve(app, host=host, port=port)
