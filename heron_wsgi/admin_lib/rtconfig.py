'''rtconfig -- access to runtime options
'''

import os
import ConfigParser

import injector

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


class MockMixin(object):
    @classmethod
    def mods(cls):
        return [cls()]

    @classmethod
    def make(cls, what=None):
        if what is None:
            what = cls.stuff
        depgraph = injector.Injector(cls.mods())
        return [depgraph.get(it) if it else depgraph
                for it in what]


class IniModule(injector.Module):
    def __init__(self, ini):
        injector.Module.__init__(self)
        if ini is None:
            ini = os.environ.get('HACONFIG', None)
            if ini is None:
                ini = 'integration-test.ini'
        self._ini = ini

    def bind_options(self, binder, names, section):
        rt = RuntimeOptions(names)
        rt.load(self._ini, section)
        binder.bind((Options, section), rt)
        return rt

    @classmethod
    def mods(cls, ini):
        return [cls(ini)]

    @classmethod
    def make(cls, ini, what):
        depgraph = injector.Injector(cls.mods(ini))
        return [depgraph.get(it) if it else depgraph
                for it in what]



