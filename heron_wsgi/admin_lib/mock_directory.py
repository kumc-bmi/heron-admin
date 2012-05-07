'''mock_directory -- Simulate medical center directory service.
===============================================================

The mock directory has a handful of students and faculty::

  >>> d = MockDirectory()
  >>> [(r['kumcPersonFaculty'], r['cn']) for r in d.records]
  ... #doctest: +NORMALIZE_WHITESPACE
  [('Y', 'john.smith'),
   ('N', 'bill.student'),
   ('N', 'carol.student'),
   ('N', 'some.one'),
   ('N', 'big.wig')]

It implements the LDAP search API in a few cases::

  >>> d.search('(cn=john.smith)', ['sn', 'givenname'])
  [('(cn=john.smith)', {'givenname': ['John'], 'sn': ['Smith']})]

It also supplies HSC training info::

  >>> d.trainedThru('john.smith')
  '2012-01-01'
'''

import pkg_resources
import csv
import re


class MockDirectory(object):
    def __init__(self, resource='mockDirectory.csv'):
        self.records = records = list(self._records(resource))
        self._d = dict([(r['cn'], r) for r in records])

    def search(self, q, attrs):
        i = self._qid(q)
        return [('(cn=%s)' % i,
                 dict([(a, [self._d[i][a]])
                       for a in attrs]))]

    def trainedThru(self, cn):
        return self._d[cn]['trainedThru']

    @classmethod
    def _records(cls, resource):
        s = pkg_resources.resource_stream(__name__, resource)
        for r in csv.DictReader(s):
            yield r

    @classmethod
    def _qid(cls, q):
        '''Extract target cn from one or two kinds of LDAP queries.

        >>> MockDirectory._qid('(cn=john.smith)')
        'john.smith'
        >>> MockDirectory._qid('(cn=john.smith*)')
        'john.smith'
        '''
        m = re.match(r'\(cn=([^*)]+)\*?\)', q)
        if m:
            return m.group(1)
        raise ValueError
