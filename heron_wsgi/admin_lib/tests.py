'''tests.py -- Run all the doctests for code coverage analysis.
---------------------------------------------------------------

.. todo:: use nose__ with doctest instead

__ http://readthedocs.org/docs/nose/en/latest/

'''
import doctest


def main():
    import hcard_mock
    doctest.testmod(hcard_mock)

    import rtconfig
    doctest.testmod(rtconfig)

    import i2b2pm
    doctest.testmod(i2b2pm)

    import ldaplib
    doctest.testmod(ldaplib)

    import medcenter
    doctest.testmod(medcenter)

    import redcap_connect
    doctest.testmod(redcap_connect)

    import heron_policy
    doctest.testmod(heron_policy)

    import checklist
    doctest.testmod(checklist)

    import redcapdb
    doctest.testmod(redcapdb)

    import disclaimer
    doctest.testmod(disclaimer)


if __name__ == '__main__':
    main()
