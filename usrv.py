'''usrv.py -- a micro web server for mustache-based site dev
'''

#python stdlib 1st, as per PEP8
import os

# pypi
import pystache

HTMLu = 'text/html; charset=utf-8'

class TemplateApp(object):
    def __init__(self, docroot='htdocs'):
        self._docroot = docroot

    def __call__(self, environ, start_response):
        path = environ['PATH_INFO']
        
        # url-decode path?
        try:
            f = open(os.path.join(self._docroot, path[1:]))
            t = f.read()
        except IOError:
            start_response("404 not found", [('Content-type', 'text/plain')])
            return 'not found: ' + path

        start_response("200 ok", [('Content-type', HTMLu)])
        return pystache.render(t)  #@@todo: params


class AVApp(TemplateApp):
    def __init__(self, av_path, av_app, docroot='htdocs'):
        TemplateApp.__init__(self, docroot)
        self._av = av_path
        self._av_app = av_app

    def __call__(self, environ, start_response):
        path = environ['PATH_INFO']

        if self._av and path.startswith(self._av):
            return self._av_app(environ, start_response)

        return TemplateApp.__call__(self, environ, start_response)


# mod_wsgi conventional entry point
#application = TemplateApp()  #@@ untested

if __name__ == '__main__':
    # test usage
    from paste import httpserver
    from paste import fileapp
    import sys
    host, port = sys.argv[1:3]
    app = AVApp('/av/', fileapp.DirectoryApp('htdocs/'))
    httpserver.serve(app, host=host, port=port)
