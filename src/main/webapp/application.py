# Listing 13-12.
# http://www.jython.org/jythonbook/en/1.0/SimpleWebApps.html
import sys
import string


def escape_html(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def cutoff(s, n=100):
    if len(s) > n:
        return s[:n] + '.. cut ..'
    return s


def handler(environ, start_response):
    start_response("200 OK", [('content-type', 'text/html')])
    return ['Hello world!']


def _x():
    response_parts = '''<html><head>
        <title>Modjy demo WSGI application running on Local Server!</title>
        </head>
        <body>
        <p>Modjy servlet running correctly:
        jython $version on $platform:
        </p>
        <h3>Hello jython WSGI on your local server!</h3>
        <h4>Here are the contents of the WSGI environment</h4>'''
    environ_str = "<table border='1'>"
    keys = environ.keys()
    keys.sort()
    for ix, name in enumerate(keys):
        if ix % 2:
            background = '#ffffff'
        else:
            background = '#eeeeee'
        style = " style='background-color:%s;'" % background
        value = escape_html(cutoff(str(environ[name]))) or '&#160;'
        environ_str = "%s\\n<tr><td%s>%s</td><td%s>%s</td></tr>" % \
            (environ_str, style, name, style, value)
    environ_str = "%s\\n</table>" % environ_str
    response_parts = response_parts + environ_str + '</body></html>\\n'
    response_text = string.Template(response_parts)
    return [response_text.substitute(
        version=sys.version, platform=sys.platform)]
