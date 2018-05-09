'''redcap_connect.py -- Connect HERON users to REDCap surveys securely.
-----------------------------------------------------------------------

Configuration gives us access to the REDCap API::

  >>> print(_test_settings.inifmt('survey_xyz'))
  [survey_xyz]
  domain=js.example
  engine=redcapdb:Mock
  project_id=34
  survey_id=11
  survey_url=http://testhost/redcap-host/surveys/?s=43

  >>> set(OPTIONS) < set(_test_settings.settings().keys())
  True

  >>> io = redcap_invite.MockIO()
  >>> setup = SurveySetup(_test_settings, io.connect, io.rng)

Set up a link to survey associated with John Smith's email address::

  >>> setup('john.smith',
  ...       {'user_id': 'john.smith', 'full_name': 'John Smith'}).split('?')
  ... # doctest: +NORMALIZE_WHITESPACE
  ['http://testhost/redcap-host/surveys/',
   's=qTwAVx&full_name=John+Smith&user_id=john.smith']

Fill in some of the fields in the survey, such as `full_name` and `what_for`::

  >>> setup('john.smith',
  ...       {'multi': 'yes', 'user_id': 'john.smith',
  ...        'what_for': '2', 'full_name': 'Smith, John'},
  ...       multi=True).split('&')
  ... # doctest: +NORMALIZE_WHITESPACE
  ['http://testhost/redcap-host/surveys/?s=qTwAVx',
   'full_name=Smith%2C+John',
   'multi=yes', 'user_id=john.smith', 'what_for=2']
'''

from __future__ import print_function
import logging
from urllib import urlencode
from urlparse import urljoin

from injector import inject, singleton, provides, Key

import rtconfig
import redcap_invite

log = logging.getLogger(__name__)

OPTIONS = ('survey_url', 'domain', 'survey_id')
KRandom = Key(__name__ + '.Random')
KInviteEngine = Key(__name__ + '.Engine')


class SurveySetup(object):
    def __init__(self, rt, connect, rng, project_id=None, survey_id=None):
        self.__ss = redcap_invite.SecureSurvey(connect, rng, survey_id)
        self.domain = rt.domain
        self.base = rt.survey_url
        self.survey_id = survey_id
        self.project_id = project_id

    def __call__(self, userid, params, multi=False):
        email = '%s@%s' % (userid, self.domain)
        surveycode = self.__ss.invite(email, multi)
        assert surveycode
        params = urlencode([('s', surveycode)]
                           + sorted(params.iteritems()))
        return urljoin(self.base, '?' + params)


_test_settings = rtconfig.TestTimeOptions(dict(
    engine='redcapdb:Mock',
    survey_url='http://testhost/redcap-host/surveys/?s=43',
    domain='js.example',
    survey_id=11,
    project_id=34))


class RunTime(rtconfig.IniModule):  # pragma: nocover
    @classmethod
    def integration_test(cls):
        from urllib2 import build_opener, Request

        mod = cls(None)
        dopts = mod.get_options(OPTIONS, 'dua_survey')
        sopts = mod.get_options(OPTIONS, 'saa_survey')
        oopts = mod.get_options(OPTIONS, 'oversight_survey')
        return s0, s1, s2

    @singleton
    @provides(KInviteEngine)
    def db_engine(self):
        from sqlalchemy import create_engine

        opts = self.get_options(('engine',), redcap_invite.CONFIG_SECTION)
        return create_engine(opts.engine)

    @singleton
    @provides(KRandom)
    def rng(self):
        from random import Random
        return Random()


def _test_multi_use(c, uid, full_name):  # pragma: nocover
    '''Test that a user can use the same survey to make multiple requests.
    '''
    from urllib2 import urlopen

    params = {'email': uid + '@kumc.edu', 'full_name': full_name}
    addr1 = c(uid, params, multi=True)

    content1 = urlopen(addr1).read()
    if 'already' in content1:
        raise ValueError('form for 1st request says ...already...')

    print("@@ The next couple tests are kinda broken.")

    addr2 = c(uid, params, multi=True)
    if addr2 == addr1:
        raise ValueError('2nd request has same address as 1st: %s = %s' % (
            addr1, addr2))

    content2 = urlopen(addr2).read()
    if 'already' in content2:
        raise ValueError('form for 2nd request says ...already...')


def _integration_test():  # pragma: nocover
    import sys
    import pprint
    logging.basicConfig(level=logging.DEBUG, stream=sys.stderr)

    userid, fullName = sys.argv[1:3]
    c0, c1, c2 = RunTime.integration_test()
    try:
        pprint.pprint(c0(userid, {'email': userid + '@kumc.edu',
                                  'full_name': fullName}))
        pprint.pprint(c1(userid, {'email': userid + '@kumc.edu',
                                  'full_name': fullName}))
        pprint.pprint(c2(userid, {'email': userid + '@kumc.edu',
                                  'full_name': fullName}))
    except IOError as e:
        print(e.message)
        print(e)

    #@@ _test_multi_use(c2, userid, fullName)


if __name__ == '__main__':  # pragma nocover
    _integration_test()
