'''redcap_connect.py -- Connect HERON users to REDCap surveys.

expects configuration a la:

[redcap]
TOKEN=...
api_url=http://redcap-host/redcap/api/
survey_url=http://bmidev1/redcap-host/surveys/
domain=example.edu
'''

import urllib
import urllib2
import pprint
import json

import config

def survey_setup(ini, section):
    rt = config.RuntimeOptions('token api_url survey_url domain'.split())
    rt.load(ini, section)

    def setup(userid, full_name):
        email = '%s@%s' % (userid, rt.domain)
        body = urllib.urlencode({'token': rt.token,
                                 'content': 'survey',
                                 'format': 'json',
                                 'email': email})
        body = urllib2.urlopen(rt.api_url, body).read()
        surveycode = json.loads(body)['hash']
        params = urllib.urlencode({'s': surveycode,
                                   'user_id': userid,
                                   'full_name': full_name})
        return rt.survey_url + '?' + params

    return setup


def _integration_test(ini='saa_survey.ini', section='saa_survey'):
    return survey_setup(ini, section)


if __name__ == '__main__':
    import sys
    from pprint import pprint
    emailAddress = sys.argv[1]
    c = _integration_test()
    pprint(c(emailAddress))
