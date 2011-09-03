import doctest

from admin_lib import tests

import heron_srv
import cas_auth
import usrv

doctest.testmod(heron_srv)
doctest.testmod(cas_auth)
doctest.testmod(usrv)
