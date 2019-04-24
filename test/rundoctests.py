# This is a horrible kludge.
# Doctests were originally developed by running one file at a time a la:
#   python -m doctest heron_srv.py
# When run under nosetests, they don't quite work. So...

from __future__ import print_function
from doctest import testmod
from sys import stderr
import logging


def main(sys_path, listdir, import_module):
    # code_dirs = ['heron_wsgi/admin_lib', 'heron_wsgi']
    code_dirs = ['heron_wsgi/admin_lib']
    sys_path.extend(code_dirs)

    wins, losses = 0, 0

    for cd in code_dirs:
        print('%s:' % cd, file=stderr)
        names = sorted(py for py in listdir(cd)
                       if py.endswith('.py')
                       and py != 'jdbc_test.py')

        for fname in names:
            name = fname[:-len('.py')]
            print('%s/%s' % (cd, name), file=stderr)
            m = import_module(name)

            # KLUDGE: reset logging
            for handler in logging.root.handlers[:]:
                logging.root.removeHandler(handler)

            (w, l) = testmod(m)
            wins, losses = wins + w, losses + l

    if losses:
        raise SystemExit(1)

# for src in *.py; do echo $src; python -m doctest $src; done


if __name__ == '__main__':
    def _script():
        from os import listdir
        from sys import path as sys_path
        from importlib import import_module

        main(sys_path, listdir, import_module)

    _script()
