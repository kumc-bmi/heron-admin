import doctest

def main():
    from admin_lib import tests as admin_tests
    admin_tests.main()

    import cas_auth
    import heron_srv
    import usrv

    doctest.testmod(cas_auth)
    doctest.testmod(heron_srv)
    doctest.testmod(usrv)


if __name__ == '__main__':
    main()
