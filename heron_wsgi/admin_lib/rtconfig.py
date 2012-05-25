'''rtconfig -- runtime configuration and dependency injection utilities
-----------------------------------------------------------------------

To instantiate classes based on runtime configuration using
injector__, use :meth:`IniModule.make`. :class:`MockMixin` provides
an analagous :meth:`MockMixin.make` method.

__ http://pypi.python.org/pypi/injector/

See also AuthorityInjection__.

__ http://informatics.kumc.edu/work/wiki/AuthorityInjection

'''

import os
import ConfigParser

import injector


class Options(object):
    def __init__(self, attrs):
        '''Create a container of options.

        :param attrs: option names. See :class:`TestTimeOptions` for example.
        '''

        self._attrs = attrs
        self._d = {}

    def __getattr__(self, n):
        if n not in self._attrs:
            raise AttributeError(n)
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
    '''Simulate :class:`RuntimeOptions` using a dictionary of values.

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
        '''Instantiate this module class and each module class it depends on.

        Note: This class has no dependencies; subclasses should
        override this method as appropriate.
        '''
        return [cls()]

    @classmethod
    def make(cls, what=None):
        '''Instantiate classes using dependency injection.

        This is analagous to :meth:`IniModule.make`, but with no
        constructor arguments.
        '''
        if what is None:
            what = cls.stuff
        modules = cls.mods()
        try:
            depgraph = injector.Injector(modules)
        except TypeError:
            raise TypeError('failed to instantiate dep. graph w.r.t. \n%s' % (
                '\n'.join([str(m) for m in modules])))
        try:
            return [depgraph.get(it) if it else depgraph
                    for it in what]
        except TypeError:
            raise TypeError('failed to instantiate: %s w.r.t. \n%s' % (
                it, '\n'.join([str(m) for m in modules])))


class IniModule(injector.Module):
    '''Provide runtime configuration in dependency injection graph.
    '''
    def __init__(self, ini):
        '''Create an injector Module that can bind :class:`Options`
        based on a section of an ini file.

        :param ini: if None, defaults to `HACONFIG` environment variable;
                    if that is not set, defaults to `integration-test.ini`.
        '''
        injector.Module.__init__(self)
        if ini is None:
            ini = os.environ.get('HACONFIG', None)
            if ini is None:
                ini = 'integration-test.ini'
        self._ini = ini

    def get_options(self, names, section):
        rt = RuntimeOptions(names)
        rt.load(self._ini, section)
        return rt

    def bind_options(self, binder, names, section):
        rt = RuntimeOptions(names)
        rt.load(self._ini, section)
        binder.bind((Options, section), rt)
        return rt

    @classmethod
    def mods(cls, ini):
        '''Instantiate this module class and each module class it depends on.

        :param ini: passed to constructor of each module.

        Note: This class has no dependencies; subclasses should
        override this method as appropriate.

        '''
        return [cls(ini)]

    @classmethod
    def make(cls, ini, what):
        '''Read configuration; instantiate classes using dependency injection.

        :param ini: passed to constructor of each module.
        :param what: list of either a class to instantiate
                     or None to get the dependency graph itself.

        Using :meth:`mods` to get a list of modules that provide bindings
        from classes (or other keys) to objects, create an `injector.Injector`
        and use it to instantiate each of the classes in `what`.
        '''
        depgraph = injector.Injector(cls.mods(ini))
        return [depgraph.get(it) if it else depgraph
                for it in what]
