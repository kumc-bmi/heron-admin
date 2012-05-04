'''hcard_mock -- mock enterprise directory based on hCard data

Usage::
  $ python -m doctest hcard_mock.py

Load the mock data::
  >>> d = MockDirectory()

Search by cn and return a couple attributes::
  >>> d.search('(cn=john.smith)', ['sn', 'givenname'])
  [('(cn=john.smith)', {'givenname': ['John'], 'sn': ['Smith']})]
  >>> d.trainedThru('john.smith')
  '2012-01-01'


*Hmm... using microformats is perhaps overkill, given python's list/dict literals.*

'''

import os
import re
import logging

from lxml import etree  # http://codespeak.net/lxml/ or python-lxml in ubuntu

log = logging.getLogger(__name__)

TEST_FILE = os.path.join(os.path.dirname(__file__), 'mockDirectory.html')


class MockDirectory(object):
    # map from ldap attributes to hcard(ish) class nams
    ldap2hcard = {"cn": None,
                  "ou": "organization-unit",
                  "sn": "family-name",
                  "givenname": "given-name",
                  "title": "title",
                  "mail": "email",
                  "kumcPersonFaculty": "kumcPersonFaculty",
                  "kumcPersonJobcode": "kumcPersonJobcode"}

    def __init__(self, filename=TEST_FILE):
        self._doc = etree.parse(open(filename))

    def _byid(self, i):
        # for testing, we don't worry too much about quotes and such in i
        return self._doc.xpath(_id_xpath(i))

    def search(self, query, attrs):
        '''Run query and return a mapping from attributes to lists of values.
        '''
        hcards = self._doc.xpath(_l2x(query))
        return [('(cn=%s)' % e.xpath('@id')[0],
                 dict([(a, [_byClass(e, self.ldap2hcard[a])]) for a in attrs]))
                for e in hcards]

    def trainedThru(self, userid):
        hcards = self._doc.xpath(_id_xpath(userid))
        if len(hcards) < 1:
            raise KeyError
        elif len(hcards) > 1:
            raise ValueError

        return _byClass(hcards[0], 'dtend')


def _l2x(q):
    '''
    >>> _l2x('(cn=john.smith)')
    '//*[@id="john.smith"]'
    >>> _l2x('(cn=john.smith*)')
    '//*[@id="john.smith"]'
    '''
    log.debug('_l2x q: %s', q)
    m = re.match(r'\(cn=([^*)]+)\*?\)', q)
    if m:
        xp = _id_xpath(m.group(1))
        log.debug('_l2x xpath: %s', xp)
        return xp
    raise ValueError


def square(x):
    '''
    >>> square(2)
    4
    '''
    return x * 2


def _id_xpath(v):
    return '//*[@id="%s"]' % v


def _byClass(e, c):
    if c:
        hits = e.xpath('.//*[@class="%s"]/text()' % c)
    else:
        hits = e.xpath('@id')
    return hits[0] if hits else ""  # hmm... "" or None?
