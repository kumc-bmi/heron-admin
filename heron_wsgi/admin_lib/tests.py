'''tests.py -- Run all the doctests for code coverage analysis.
---------------------------------------------------------------

.. todo:: use nose__ with doctest instead

__ http://readthedocs.org/docs/nose/en/latest/

'''

import os
import subprocess


def main():
    pyfiles = [f for f in os.listdir('.')
               if f.endswith('.py')]
    for pf in pyfiles:
        subprocess.call(('python', '-m', 'doctest', pf))


if __name__ == '__main__':
    main()
