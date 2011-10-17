'''config.py -- access to runtime options
'''

import ConfigParser

class Options(object):
    def __init__(self, attrs):
        self._attrs = attrs
        self._d = {}

    def __getattr__(self, n):
        if n not in self._attrs:
            raise AttributeError, n
        return self._d.get(n, None)

    def inifmt(self, section):
        # oops... redundant w.r.t. ConfigParser.write() and String()
        s = self._d
        lines = ['%s=%s' % (k, s[k]) for k in sorted(s.keys())]
        return '\n'.join(["[%s]" % section] + lines)

    def settings(self):
        return self._d

    def __repr__(self):
        return 'Options(%s / %s)' % (sorted(self._attrs),
                                     sorted(self._d.keys()))


class RuntimeOptions(Options):  # pragma nocover
    def load(self, ini, section):
        p = ConfigParser.SafeConfigParser()
        p.read(ini)
        self._d = dict(p.items(section))
        return self


class TestTimeOptions(RuntimeOptions):
    '''
      >>> tto = TestTimeOptions({'size': '10', 'color': 'blue'})
      >>> print tto.inifmt('widget')
      [widget]
      color=blue
      size=10

    Some 'static' checking:
      >>> tto.typo
      Traceback (most recent call last):
          ...
      AttributeError: typo
    '''
    def __init__(self, settings):
        Options.__init__(self, settings.keys())
        self._d = settings
