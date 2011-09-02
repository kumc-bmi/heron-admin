'''medcenter.py -- academic medical center directory/policy

  >>> m = _doctester()

  >>> a1 = m.affiliate('john.smith')
  >>> a1
  John Smith <john.smith@js.example>
  >>> a1.title
  'Chair of Department of Neurology'

'''

import os
import sys
import urllib
import urllib2

import config

class MedCenter(object):
    excluded_jobcode = "24600"

    def __init__(self, searchsvc, trainingfn):
        self._svc = searchsvc
        self._training = trainingfn

    def affiliate(self, name):
        matches = self._svc.search('(cn=%s)' % name, AccountHolder.attributes)
        if len(matches) != 1:
            if len(matches) == 0:
                raise KeyError, name
            else:
                raise ValueError, name  # ambiguous

        dn, attrs = matches[0]

        return AccountHolder(extract_values(attrs))

    def trainedThru(self, who):
        return self._training(who.userid())


    def checkFaculty(self, who):
        if (who.kumcPersonJobcode != self.excluded_jobcode
            and who.kumcPersonFaculty == 'Y'):
            return
        raise NotFaculty()

    def affiliateSearch(self, max_qty, cn, sn, givenname):
        clauses = ['(%s=%s*)' % (n, v)
                   for (n, v) in (('cn', cn), ('sn', sn), ('givenname', givenname))
                   if v]
        if len(clauses) == 0:
            return ()

        if len(clauses) > 1:
            q = '(&' + (''.join(clauses)) + ')'
        else:
            q = clauses[0]

        results = self._svc.search(q, AccountHolder.attributes)[:max_qty]
        return [AccountHolder(extract_values(attrs))
                for dn, attrs in results]


def extract_values(attrs):
    return [attrs.get(n, [None])[0]
            for n in AccountHolder.attributes]


class NotFaculty(Exception):
    pass


class AccountHolder(object):
    '''
    Note: KUMC uses ou for department.
    '''
    attributes = ["cn", "ou", "sn", "givenname", "title", "mail",
                  "kumcPersonFaculty", "kumcPersonJobcode"]

    def __init__(self, values):
        self._attrs = dict(zip(self.attributes, values))

    def __str__(self):
        return '%s %s <%s>' % (self.givenname, self.sn, self.mail)

    def __repr__(self):
        return str(self)

    def userid(self):
        # TODO: use python property stuff?
        return self.cn

    def __getattr__(self, n):
        if n not in self.attributes:
            raise AttributeError
        return self._attrs[n]


def chalkdb_queryfn(ini, section):
    rt = config.RuntimeOptions('url param'.split())
    rt.load(ini, section)

    def training_expiration(userid):
        addr = rt.url + '?' + urllib.urlencode({rt.param: userid})
        body = urllib2.urlopen(addr).read()

        if not body:  # no expiration on file
            raise KeyError

        return body.strip()  # get rid of newline
    return training_expiration


def _doctester():
    import hcard_mock
    d = hcard_mock.MockDirectory(hcard_mock.TEST_FILE)
    return MedCenter(d, d.trainedThru)


def _integration_test(ini='integration-test.ini', chalk_section='chalk'):
    import ldaplib

    cq = chalkdb_queryfn(ini, chalk_section)

    return MedCenter(ldaplib._integration_test(), cq)



if __name__ == '__main__':
    import pprint

    if '--search' in sys.argv:
        cn, sn, givenname = sys.argv[2:5]
        m = _integration_test()
        print [10, cn, sn, givenname]
        print m.affiliateSearch(10, cn, sn, givenname)
    else:
        uid = sys.argv[1]
        m = _integration_test()

        who = m.affiliate(uid)
        print who
        print "training: ", m.trainedThru(who)
