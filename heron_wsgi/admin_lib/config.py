'''config.py -- access to runtime options
'''

import ConfigParser

class RuntimeOptions(object):
    def __init__(self, attrs):
        self._attrs = attrs
        self._d = {}

    def load(self, ini, section):
        p = ConfigParser.SafeConfigParser()
        p.read(ini)
        self._d = dict(p.items(section))

    def __getattr__(self, n):
        if n not in self._attrs:
            raise AttributeError, n
        return self._d.get(n, None)


class TestTimeOptions(object):
    '''
      >>> tto = TestTimeOptions({'size': '10', 'color': 'blue'})
      >>> print tto.inifmt('widget')
      [widget]
      color=blue
      size=10

    '''
    def __init__(self, settings):
        self._settings = settings

    def __getattr__(self, n):
        if n not in self._settings:
            raise AttributeError, n
        return self._settings[n]
        
    def inifmt(self, section):
        s = self._settings
        lines = ['%s=%s' % (k, s[k]) for k in sorted(s.keys())]
        return '\n'.join(["[%s]" % section] + lines)
