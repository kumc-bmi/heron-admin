'''usrv.py -- a micro web server for mustache-based site dev

'''

# stdlib imports 1st per
# PEP 8 -- Style Guide for Python Code
# http://www.python.org/dev/peps/pep-0008/
import os
import wsgiref.util as wsgi

# from PyPI - the Python Package Index http://pypi.python.org/pypi
from genshi.template import MarkupTemplate, TemplateLoader, TemplateNotFound

# see http://code.google.com/p/modwsgi/wiki/VirtualEnvironments 
import site
from os.path import join, dirname
site.addsitedir(dirname(__file__))

import cas_auth

HTMLu = 'text/html; charset=utf-8'


class TemplateApp(object):
    def __init__(self, docroot=None):
        if docroot is None:
            docroot = os.path.join(dirname(__file__), 'htdocs')
        self._docroot = docroot
        self._loader = TemplateLoader([docroot], auto_reload=True)

    def __call__(self, environ, start_response):
        path = environ['PATH_INFO']
        session = environ['beaker.session']

        if path == '/':
            path = '/index.html'

        # url-decode path?
        try:
            tmpl = self._loader.load(path[1:])
            raven_home = wsgi.application_uri(environ)
            if not raven_home.endswith('/'):
                raven_home = raven_home + '/'
            stream = tmpl.generate(user=session['user'],
                                   raven_home=raven_home)
            body = stream.render('xhtml')
        except TemplateNotFound as e:
            start_response("404 not found", [('Content-type', 'text/plain')])
            #debug: return ['docroot: ', self._docroot, '  ', str(e)]
            return 'We have no page at that address. Broken link? Typo?'

        start_response("200 ok", [('Content-type', HTMLu)])
        return body


class PathPrefix(object):
    '''micro-router
    '''
    def __init__(self, prefix, app, next):
        self._prefix = prefix
        self._app = app
        self._next = next

    def __call__(self, environ, start_response):
        path = environ['PATH_INFO']

        if path.startswith(self._prefix):
            return self._app(environ, start_response)
        else:
            return self._next(environ, start_response)


def _mkapp(cas='https://cas.kumc.edu/cas/', auth_area='/u/',
           login='/login', logout='/u/logout'):
    t = TemplateApp()
    return cas_auth.cas_required(cas, 'raven', PathPrefix,
                                 login, logout, t)

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
    app = PathPrefix('/av/', fileapp.DirectoryApp('htdocs/'), application)

    httpserver.serve(app, host=host, port=port)
