'''redcap_connect.py -- Connect HERON users to REDCap surveys.

  >>> print _test_settings.inifmt('survey_xyz')
  [survey_xyz]
  api_url=http://redcap-host/redcap/api/
  domain=example.edu
  executives=big.wig
  project_id=34
  survey_id=11
  survey_url=http://bmidev1/redcap-host/surveys/
  token=sekret

  >>> setup = survey_setup(_test_settings, _TestUrlOpener())
  >>> setup('john.smith',
  ...       {'user_id': 'john.smith', 'full_name': 'John Smith'}).split('?')
  ... # doctest: +NORMALIZE_WHITESPACE
  ['http://bmidev1/redcap-host/surveys/',
   's=8074&full_name=John+Smith&user_id=john.smith']


'''

import json
import logging
import sys
import urllib

import config

log = logging.getLogger(__name__)


def settings(ini, section, extras=None):
    rt = config.RuntimeOptions('token api_url survey_url domain survey_id'
                               .split() + ([] if extras is None else extras))
    rt.load(ini, section)
    return rt


def survey_setup(rt, urlopener):
    def setup(userid, params, multi=False):
        email = '%s@%s' % (userid, rt.domain)
        args = {'token': rt.token,
                'content': 'survey',
                'format': 'json',
                'multi': 'yes' if multi else 'no',
                'email': email}
        log.debug('POSTing %s to redcap at %s', args, rt.api_url)
        body = urlopener.open(rt.api_url, urllib.urlencode(args)).read()
        ans = json.loads(body)
        log.info('REDCap API answer: %s', ans)
        surveycode = ans['hash']
        params = urllib.urlencode([('s', surveycode)]
                                  + sorted(params.iteritems()))
        return rt.survey_url + '?' + params

    return setup


class _TestUrlOpener(object):
    def open(self, addr, _):  # pylint: disable=R0201
                              # class wouldn't work.
        return _TestResponse(hex(abs(hash(addr)))[-4:])

class _TestResponse(object):
    def __init__(self, h):
        self._h = h

    def read(self):
        return json.dumps({'PROJECT_ID': 123,
                           'add': 0,
                           'survey_id': _test_settings.survey_id,
                           'hash': self._h,
                           'email': u'BOGUS@%s' % _test_settings.domain})

_test_settings = config.TestTimeOptions(dict(
    token='sekret',
    api_url='http://redcap-host/redcap/api/',
    survey_url='http://bmidev1/redcap-host/surveys/',
    domain='example.edu',
    executives='big.wig',
    survey_id=11,
    project_id=34))


def _integration_test(ini='integration-test.ini',
                      section1='saa_survey',
                      section2='oversight_survey'):  # pragma nocover
    s1 = survey_setup(settings(ini, section1), urllib.URLopener())
    s2 = survey_setup(settings(ini, section2), urllib.URLopener())
    return s1, s2


def _test_multi_use(c, uid, full_name, ua):
    '''Test that a user can use the same survey to make multiple requests.
    '''
    params = {'email': uid + '@kumc.edu', 'full_name': full_name}
    addr1 = c(uid, params, multi=True)

    content1 = ua.open(addr1).read()
    if 'already' in content1:
        raise ValueError, 'form for 1st request says ...already...'

    # @@ need to fill it out.

    addr2 = c(uid, params, multi=True)
    if addr2 == addr1:
        raise ValueError, '2nd request has same address as 1st: %s = %s' % (
            addr1, addr2)

    content2 = ua.open(addr2).read()
    if 'already' in content2:
        raise ValueError, 'form for 2nd request says ...already...'

    

def _test_main():
    from pprint import pprint  # pylint: disable=W0404

    logging.basicConfig(level=logging.DEBUG, stream=sys.stderr)

    userid, fullName = sys.argv[1:3]
    c1, c2 = _integration_test()
    try:
        pprint(c1(userid, {'email': userid + '@kumc.edu',
                           'full_name': fullName}))
        pprint(c2(userid, {'email': userid + '@kumc.edu',
                           'full_name': fullName}))
    except IOError, e:
        print e.message
        print e

    _test_multi_use(c2, userid, fullName, urllib.URLopener())

if __name__ == '__main__':  # pragma nocover
    _test_main()
