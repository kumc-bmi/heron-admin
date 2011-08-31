'''redcap_connect.py -- Connect HERON users to REDCap surveys.

expects redcap.ini a la:

[redcap]
TOKEN=...
api_url=http://redcap-host/redcap/api/
survey_url=http://bmidev1/redcap-host/surveys/?s=

'''

import urllib
import urllib2
import pprint
import json

import config

def survey_setup(ini, section):
    #TODO: split on this side of call
    rt = config.RuntimeOptions('token api_url survey_url')
    rt.load(ini, section)

    def setup(addr):
        body = urllib.urlencode({'token': rt.token,
                                 'content': 'survey',
                                 'format': 'json',
                                 'email': addr})
        body = urllib2.urlopen(rt.api_url, body).read()
        hashcode = json.loads(body)['hash']
        return rt.survey_url + hashcode

    return setup


def _integration_test(ini='redcap.ini', section='redcap'):
    return survey_setup(ini, section)


if __name__ == '__main__':
    import sys
    from pprint import pprint
    emailAddress = sys.argv[1]
    c = _integration_test()
    pprint(c(emailAddress))
