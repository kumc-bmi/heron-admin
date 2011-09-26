'''tests.py -- run all the doctests for code coverage analysis.
'''
import doctest

def main():
    import checklist
    import config
    import db_util
    import hcard_mock
    import heron_policy
    import i2b2pm
    import ldaplib
    import medcenter
    import redcap_connect

    doctest.testmod(checklist)
    doctest.testmod(config)
    doctest.testmod(db_util)
    doctest.testmod(hcard_mock)
    doctest.testmod(heron_policy)
    doctest.testmod(i2b2pm)
    doctest.testmod(ldaplib)
    doctest.testmod(medcenter)
    doctest.testmod(redcap_connect)

if __name__ == '__main__':
    main()
