'''usrv.py -- a micro web server for mustache-based site dev
'''

#python stdlib 1st, as per PEP8
import os

# pypi
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
            stream = tmpl.generate() #@@todo: params
            body = stream.render('xhtml')
        except TemplateNotFound as e:
            start_response("404 not found", [('Content-type', 'text/plain')])
            return str(e)

        start_response("200 ok", [('Content-type', HTMLu)])
        return body


def _mkapp(cas='https://cas.kumc.edu/cas/', auth_area='/u/'):
    t = TemplateApp()
    return cas_auth.CASRequired(cas, auth_area, t, t)

# mod_wsgi conventional entry point
application = _mkapp()
                                   

class AVApp(object):
    '''In production use, static A/V media files would be
    served with apache, but for test purposes, we'll use
    this.
    '''
    def __init__(self, av_path, av_app, next):
        self._av = av_path
        self._av_app = av_app
        self._next = next

    def __call__(self, environ, start_response):
        path = environ['PATH_INFO']

        if self._av and path.startswith(self._av):
            return self._av_app(environ, start_response)
        else:
            return self._next(environ, start_response)

if __name__ == '__main__':
    # test usage
    from paste import httpserver
    from paste import fileapp
    import sys
    host, port = sys.argv[1:3]

    app = AVApp('/av/', fileapp.DirectoryApp('htdocs/'), application)
    httpserver.serve(app, host=host, port=port)
