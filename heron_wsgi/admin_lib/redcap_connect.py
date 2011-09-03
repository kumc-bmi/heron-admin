'''redcap_connect.py -- Connect HERON users to REDCap surveys.

  >>> print _test_settings.inifmt('survey_xyz')
  [survey_xyz]
  api_url=http://redcap-host/redcap/api/
  domain=example.edu
  survey_id=11
  survey_url=http://bmidev1/redcap-host/surveys/
  token=sekret

  >>> setup = survey_setup(_test_settings, _TestUrlOpener())
  >>> setup('john.smith@js.example', 'John Smith')
  'http://bmidev1/redcap-host/surveys/?s=xyzpdq&user_id=john.smith%40js.example&full_name=John+Smith'

'''

import urllib
import urllib2
import pprint
import json

import config

def settings(ini, section):
    rt = config.RuntimeOptions('token api_url survey_url domain survey_id'.split())
    rt.load(ini, section)
    return rt


def survey_setup(rt, urlopener=urllib2):
    def setup(userid, full_name):
        email = '%s@%s' % (userid, rt.domain)
        body = urllib.urlencode({'token': rt.token,
                                 'content': 'survey',
                                 'format': 'json',
                                 'email': email})
        body = urlopener.urlopen(rt.api_url, body).read()
        surveycode = json.loads(body)['hash']
        params = urllib.urlencode({'s': surveycode,
                                   'user_id': userid,
                                   'full_name': full_name})
        return rt.survey_url + '?' + params

    return setup


class _TestUrlOpener(object):
    def urlopen(self, addr, body):
        return _TestResponse()

class _TestResponse(object):
    def read(self):
        return json.dumps({'PROJECT_ID': 123,
                           'add': 0,
                           'survey_id': _test_settings.survey_id,
                           'hash': u'xyzpdq',
                           'email': u'BOGUS@%s' % _test_settings.domain})

_test_settings = config.TestTimeOptions(dict(
    token='sekret',
    api_url='http://redcap-host/redcap/api/',
    survey_url='http://bmidev1/redcap-host/surveys/',
    domain='example.edu',
    survey_id=11))


def _mock():
    return survey_setup(_test_settings, _TestUrlOpener())


def _integration_test(ini='integration-test.ini', section='saa_survey'):  # pragma nocover
    return survey_setup(settings(ini, section))


if __name__ == '__main__':  # pragma nocover
    import sys
    from pprint import pprint
    userid, fullName = sys.argv[1:3]
    c = _integration_test()
    try:
        pprint(c(userid, fullName))
    except IOError, e:
        print e.message
        print e
