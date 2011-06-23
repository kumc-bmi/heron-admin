'''usrv.py -- a micro web server for mustache-based site dev

'''

# stdlib imports 1st per
# PEP 8 -- Style Guide for Python Code
# http://www.python.org/dev/peps/pep-0008/
import os
from urlparse import urljoin

# from PyPI - the Python Package Index http://pypi.python.org/pypi
from genshi.template import MarkupTemplate, TemplateLoader, TemplateNotFound

import cas_auth

HTMLu = 'text/html; charset=utf-8'


class TemplateApp(object):
    def __init__(self, docroot='htdocs'):
        self._docroot = docroot
        self._loader = TemplateLoader([docroot], auto_reload=True)

    def __call__(self, environ, start_response):
        path = environ['PATH_INFO']

        # url-decode path?
        try:
            tmpl = self._loader.load(path[1:])
            stream = tmpl.generate(user=environ.get('REMOTE_USER', ''))
            body = stream.render('xhtml')
        except TemplateNotFound as e:
            start_response("404 not found", [('Content-type', 'text/plain')])
            return str(e)

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
           logout='/u/logout'):
    t = TemplateApp()
    protected, s = cas_auth.cas_required(cas, t)
    bye = cas_auth.logout(urljoin(cas, 'logout'), s)
    return PathPrefix(logout, bye,
                      PathPrefix(auth_area, protected, t))

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
