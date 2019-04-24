'''setup.py -- heron_wsgi package information

ref: `Creating a Pyramid Project`__

__ https://docs.pylonsproject.org/projects/pyramid/en/1.10-branch/narr/project.html

'''

__author__ = 'Dan Connolly <dconnolly@kumc.edu>'
__copyright__ = '(c) 2011-2019 University of Kansas Medical Center'
__contact__ = 'http://informatics.kumc.edu/work/wiki/HeronAdminDev'
__license__ = 'Apache 2'
__version__ = '0.7'

from ConfigParser import ConfigParser
from ast import literal_eval
import warnings


def main(cwd, version_info, setup, find_packages):
    if version_info < (2, 7, 0):
        warnings.warn('python 2.7 required')

    source = (cwd / __file__).parent
    README = (source / 'README.rst').open().read()

    # CHANGES = 'TODO'

    pipfile = ConfigParser()
    pipfile.readfp((source / 'Pipfile').open(), 'Pipfile')
    packages = pipfile.items('packages')
    requires = [pkg + ('' if spec == '*' else spec)
                for (rhs, lhs) in packages
                for (pkg, spec) in [(rhs, literal_eval(lhs))]]

    [author, author_email] = [part[:-1] for part in __author__.split('<', 1)]
    setup(name='heron_wsgi',
          version=__version__,
          description=README.split('\n', 1)[0],
          long_description=README,
          classifiers=[
            "Programming Language :: Python",
            "Topic :: Internet :: WWW/HTTP",
            "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
          ],
          author=author,
          author_email=author_email,
          url=__contact__,
          license=__license__,
          keywords='web wsgi hipaa policy enforcement',
          packages=find_packages(),
          include_package_data=True,
          zip_safe=False,
          # TODO: learn how test_suite works
          #     test_suite='heron_acct',
          # extras_require={
          #     'testing': tests_require,
          # },
          install_requires=requires,
          entry_points={
            'paste.app_factory': [
                'main = heron_wsgi:main',
            ]
          },
          paster_plugins=['pyramid'])


class Path(object):
    '''Just the parts of the pathlib API that we use.

    :type joinpath: (*str) -> Path
    :type open: (...) -> Path
    :type exists: () -> bool
    :type listdir: (str) -> Iterable[str]

    ISSUE: copy-paste from heron_wsgi.admin_lib.ocap_file
    '''
    def __init__(self, here, open, joinpath, splitpath):
        '''
        :param str here:
        '''
        make = lambda p: Path(p, open=open, joinpath=joinpath, splitpath=splitpath)
        self.joinpath = lambda there: make(joinpath(here, there))
        self.open = lambda **kwargs: open(here, **kwargs)
        self._parent = lambda: make(splitpath(here)[0])
        self._path = here

    @property
    def parent(self):
        return self._parent()

    def __repr__(self):
        return '{cls}({p})'.format(cls=self.__class__.__name__, p=self._path)

    def __str__(self):
        return self._path

    def __div__(self, there):
        '''
        :param str there:
        :rtype: Path
        '''
        return self.joinpath(there)


if __name__ == '__main__':
    def _script():
        # Access ambient authority only when invoked as a script.
        # See devdoc/ocaps.rst
        from io import open as io_open
        from os.path import join as joinpath, split as splitpath
        from sys import version_info

        from setuptools import setup, find_packages

        cwd = Path('.', open=io_open, joinpath=joinpath, splitpath=splitpath)

        main(cwd, version_info, setup, find_packages)

    _script()
