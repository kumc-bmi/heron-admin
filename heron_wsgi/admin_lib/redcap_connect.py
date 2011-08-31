'''redcap_connect.py -- Connect HERON users to REDCap surveys.

.. todo: The goal is to set up authenticated REDCap surveys, but so
         far we just managed to exercise the API.

'''

import urllib
import urllib2
import pprint

import config

def survey_setup(ini, section):
    rt = config.RuntimeOptions('url token')  #TODO: split on this side of call
    rt.load(ini, section)

    def setup(survey, addr):
        body = urllib.urlencode({'token': rt.token,
                                 'content': 'survey',
                                 'format': 'json',
                                 'survey': survey,
                                 'emailAddress': addr})
        return urllib2.urlopen(rt.url, body)

    return setup


def _integration_test(ini='redcap.ini', section='redcap'):
    return survey_setup(ini, section)


if __name__ == '__main__':
    import sys
    survey, emailAddress = sys.argv[1:3]
    c = _integration_test()
    response = c(survey, emailAddress)
    pprint.pprint(response.info().headers)
    print response.read()
