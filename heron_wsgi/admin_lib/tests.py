'''tests.py -- Run all the doctests for code coverage analysis.
---------------------------------------------------------------

.. todo:: use nose__ with doctest instead

__ http://readthedocs.org/docs/nose/en/latest/

'''
import doctest


def main():
    import sealing
    doctest.testmod(sealing)

    import ocap_file
    doctest.testmod(ocap_file)

    import jndi_util
    doctest.testmod(jndi_util)

    import mock_directory
    doctest.testmod(mock_directory)

    import rtconfig
    doctest.testmod(rtconfig)

    import ldaplib
    doctest.testmod(ldaplib)

    import medcenter
    doctest.testmod(medcenter)

    import redcap_connect
    doctest.testmod(redcap_connect)

    import i2b2pm
    doctest.testmod(i2b2pm)

    import heron_policy
    doctest.testmod(heron_policy)

    import noticelog
    doctest.testmod(noticelog)

    import redcapdb
    doctest.testmod(redcapdb)

    import disclaimer
    doctest.testmod(disclaimer)


if __name__ == '__main__':
    main()
