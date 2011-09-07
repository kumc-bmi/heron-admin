'''tests.py -- run all the doctests for code coverage analysis.
'''
import doctest

import checklist
import config
import db_util
import hcard_mock
import heron_policy
import medcenter
import redcap_connect

doctest.testmod(checklist)
doctest.testmod(config)
doctest.testmod(db_util)
doctest.testmod(hcard_mock)
doctest.testmod(heron_policy)
doctest.testmod(medcenter)
doctest.testmod(redcap_connect)
