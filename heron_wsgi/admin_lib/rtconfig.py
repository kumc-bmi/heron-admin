'''rtconfig -- runtime configuration and dependency injection utilities
-----------------------------------------------------------------------

To instantiate classes based on runtime configuration using
injector__, use :meth:`IniModule.make`. :class:`MockMixin` provides
an analagous :meth:`MockMixin.make` method.

__ http://pypi.python.org/pypi/injector/

See also AuthorityInjection__.

__ http://informatics.kumc.edu/work/wiki/AuthorityInjection

'''

import ConfigParser
import logging

import injector
from injector import provides, singleton


class Options(object):
    def __init__(self, attrs, d):
        '''Create a container of options.

        :param attrs: option names. See :class:`TestTimeOptions` for example.
        '''

        self._attrs = attrs
        self._d = d

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


class Calendar(object):
    def today(self):
        raise NotImplementedError


class Clock(object):
    def now(self):
        raise NotImplementedError


class MockClock(object):
    '''
    >>> s = MockClock()
    >>> now = s.now
    >>> now()
    datetime.datetime(2011, 9, 2, 0, 0, 0, 500000)
    >>> now()
    datetime.datetime(2011, 9, 2, 0, 0, 1)
    '''
    def __init__(self):
        import datetime
        self._t = datetime.datetime(2011, 9, 2)

    def now(self):
        self.wait(seconds=0.5)
        return self._t

    def today(self):
        return self._t.date()

    def wait(self, seconds):
        import datetime
        self._t = self._t + datetime.timedelta(seconds=seconds)


class MockClockInjector(injector.Module):
    @provides(Clock)
    def clock(self):
        return MockClock()


class RealClockInjector(injector.Module):
    def __init__(self, timesrc):
        self.__timesrc = timesrc
        self.label = '%s(%s)' % (self.__class__.__name__, timesrc.now())

    def __repr__(self):
        return self.label

    @singleton
    @provides(Clock)
    def the_clock(self):
        return self.__timesrc


def _printLogs(level=logging.INFO):
    buf = []

    class DoctestHandler(logging.Handler):
        def emit(self, record):
            msg = self.format(record)
            buf.append(msg)

    class FileNameFormatter(logging.Formatter):
        """Only show module name, not path.
        """
        def format(self, record):
            record.name = record.name.split('.')[-1]
            return logging.Formatter.format(self, record)

    root = logging.Logger.root
    f = FileNameFormatter(logging.BASIC_FORMAT)
    h = DoctestHandler()
    h.setFormatter(f)
    root.setLevel(level)
    root.addHandler(h)

    def show():
        s = '\n'.join(buf)
        buf[:] = []
        return s

    return show


class RuntimeOptions(Options):  # pragma nocover
    def __init__(self, ini, attrs, section):
        p = ConfigParser.SafeConfigParser()
        with ini.open() as stream:
            p.readfp(stream, str(ini))
        Options.__init__(self, attrs, dict(p.items(section)))


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
        Options.__init__(self, settings.keys(), settings)


class _Maker(object):
    @classmethod
    def make(cls, what, **kwargs):
        '''Read configuration; instantiate classes using dependency injection.

        :param what: list of either a class to instantiate
                     or None to get the dependency graph itself.
        :param powers: powers needed by dependencies

        Using :meth:`mods` to get a list of modules that provide bindings
        from classes (or other keys) to objects, create an `injector.Injector`
        and use it to instantiate each of the classes in `what`.
        '''
        # _logged(('make', cls, kwargs))
        modules = cls.mods(**kwargs)
        depgraph = injector.Injector(modules)
        it = None
        try:
            return [depgraph.get(it) if it else depgraph
                    for it in what]
        except TypeError as oops:
            raise TypeError('failed (%s) to instantiate: %s w.r.t. \n%s' % (
                oops, it, '\n'.join([str(m) for m in modules])))


class MockMixin(_Maker):
    @classmethod
    def mods(cls):
        '''Instantiate this module class and each module class it depends on.

        Note: This class has no dependencies; subclasses should
        override this method as appropriate.
        '''
        return [cls()]


class IniModule(injector.Module, _Maker):  # pragma: nocover
    '''Provide runtime configuration in dependency injection graph.
    '''
    def __init__(self, ini, **kwargs):
        '''Create an injector Module that can bind :class:`Options`
        based on a section of an ini file.

        :param Path ini: access to config file
        '''
        injector.Module.__init__(self)
        self.__ini = ini

    def get_options(self, names, section):
        return RuntimeOptions(self.__ini, names, section)

    def bind_options(self, binder, names, section):
        rt = RuntimeOptions(self.__ini, names, section)
        binder.bind((Options, section), rt)
        return rt

    @classmethod
    def mods(cls, ini, **kwargs):
        '''Instantiate this module class and each module class it depends on.

        Note: Subclasses must override this method as appropriate.

        '''
        return [cls(ini, **kwargs)]


def _logged(x):
    from sys import stderr
    from pprint import pprint

    pprint(x, stream=stderr)
    return x
