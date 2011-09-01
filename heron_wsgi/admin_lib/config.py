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

