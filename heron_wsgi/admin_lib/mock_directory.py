'''mock_directory -- Simulate medical center directory service.
===============================================================

The mock directory has a handful of students and faculty::

  >>> d = MockDirectory()
  >>> [(r['kumcPersonFaculty'], r['cn']) for r in d.records]
  ... #doctest: +NORMALIZE_WHITESPACE
  [('Y', 'john.smith'),
   ('N', 'bill.student'),
   ('', 'carol.student'),
   ('N', 'some.one'),
   ('N', 'big.wig')]

It implements the LDAP search API in a few cases::

  >>> d.search('(cn=john.smith)', ['sn', 'givenname'])
  [('(cn=john.smith)', {'givenname': ['John'], 'sn': ['Smith']})]

  >>> d.search('(cn=john.smith)', [])
  ... #doctest: +NORMALIZE_WHITESPACE
  [('(cn=john.smith)',
   {'kumcPersonJobcode': ['1234'], 'kumcPersonFaculty': ['Y'],
    'cn': ['john.smith'], 'title': ['Chair of Department of Neurology'],
    'trainedThru': ['2012-01-01'], 'sn': ['Smith'],
    'mail': ['john.smith@js.example'], 'ou': ['Neurology'],
    'givenname': ['John']})]

.. todo:: Make the two tests above independent of order of dictionary keys.

It also supplies HSC training info::

  >>> d.trainedThru('john.smith')
  '2012-01-01'
'''

import pkg_resources
import csv
import re
import logging

log = logging.getLogger(__name__)


class MockDirectory(object):
    def __init__(self, resource='mockDirectory.csv'):
        self.records = records = list(self._records(resource))
        self._d = dict([(r['cn'], r) for r in records])

    def search(self, q, attrs):
        log.info('network fetch for %s', q)
        i = self._qid(q)
        record = self._d[i]
        return [('(cn=%s)' % i,
                 dict([(a, [record[a]])
                       for a in (attrs or record.keys())
                       if record[a] != '']))]

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
