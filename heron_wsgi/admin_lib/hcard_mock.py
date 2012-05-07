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

    def items(self):
        for e in self._doc.xpath('//*[@id]'):
            yield e.attrib['id']


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


def _id_xpath(v):
    return '//*[@id="%s"]' % v


def _byClass(e, c):
    if c:
        hits = e.xpath('.//*[@class="%s"]/text()' % c)
    else:
        hits = e.xpath('@id')
    return hits[0] if hits else ""  # hmm... "" or None?


def _to_csv(out):
    import pprint
    import csv
    columns = ('sn cn givenname mail title ou '
               'kumcPersonJobcode kumcPersonFaculty').split()
    assert(set(MockDirectory.ldap2hcard.keys()) == set(columns))

    d = MockDirectory()
    records = [dict([(k, v[0]) for k, v in data.iteritems()])
        for _q, data in
        [hit
         for i in d.items()
         for hit in d.search('(cn=%s)' % i, columns)]]
    log.debug('records: %s', pprint.pformat(records))

    columns.append('trainedThru')

    out = csv.DictWriter(out, columns)
    out.writerow(dict(zip(columns, columns)))
    for r in records:
        r['trainedThru'] = d.trainedThru(r['cn'])
        out.writerow(r)


if __name__ == '__main__':
    import sys
    logging.basicConfig(level=logging.DEBUG)
    _to_csv(sys.stdout)
