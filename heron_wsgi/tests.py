import sys
import doctest
from contextlib import contextmanager
import urllib

def main():
    from admin_lib import tests as admin_tests
    admin_tests.main()

    import heron_srv
    doctest.testmod(heron_srv)

    import cas_auth
    doctest.testmod(cas_auth)

    import usrv
    doctest.testmod(usrv)


class LinesUrlOpener(object):
    '''An URL opener to help with CAS testing
    '''
    def __init__(self, lines):
        self._lines = lines

    def open(self, addr, body=None):
        return LinesResponse(self._lines)

class LinesResponse(object):
    def __init__(self, lines):
        self._lines = lines

    def read(self):
        return '\n'.join(self._lines)


@contextmanager
def default_urlopener(u):
    sv = urllib._urlopener
    urllib._urlopener = u
    try:
        yield None
    finally:
        urllib._urlopener = sv

        
if __name__ == '__main__':
    main()
