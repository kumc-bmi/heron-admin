'''redcap_connect.py -- Connect HERON users to REDCap surveys.

'''

import urllib
import urllib2
import pprint

import config

def survey_setup(ini, section):
    rt = config.RuntimeOptions('url token')  #TODO: split on this side of call
    rt.load(ini, section)

    def setup(addr):
        body = urllib.urlencode({'token': rt.token,
                                 'content': 'survey',
                                 'format': 'json',
                                 'email': addr})
        return urllib2.urlopen(rt.url, body)

    return setup


def _integration_test(ini='redcap.ini', section='redcap'):
    return survey_setup(ini, section)


if __name__ == '__main__':
    import sys
    emailAddress = sys.argv[1]
    c = _integration_test()
    response = c(emailAddress)
    pprint.pprint(response.info().headers)
    print response.read()
