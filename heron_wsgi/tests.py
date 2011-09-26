import doctest

def main():
    from admin_lib import tests as admin_tests
    admin_tests.main()

    import heron_srv
    doctest.testmod(heron_srv)

    import cas_auth
    doctest.testmod(cas_auth)

    import usrv
    doctest.testmod(usrv)


if __name__ == '__main__':
    main()
