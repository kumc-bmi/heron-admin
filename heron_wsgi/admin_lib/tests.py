'''tests.py -- run all the doctests for code coverage analysis.

.. todo:: use nose with doctest instead

'''
import doctest

def main():
    import hcard_mock
    doctest.testmod(hcard_mock)

    import config
    doctest.testmod(config)

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
    doctest.testmod(redcap_connect)


if __name__ == '__main__':
    main()
