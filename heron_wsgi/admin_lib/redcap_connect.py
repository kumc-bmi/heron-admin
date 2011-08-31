'''redcap_connect.py -- Connect HERON users to REDCap surveys.

.. todo: The goal is to set up authenticated REDCap surveys, but so
         far we just managed to exercise the API.

'''

import urllib
import urllib2
import pprint

import config

def connector(ini, section):
    rt = config.RuntimeOptions('url token')  #TODO: split on this side of call
    rt.load(ini, section)

    def record():
        body = urllib.urlencode({'token': rt.token,
                                 'content': 'record',
                                 'format': 'json',
                                 'type': 'eav'})
        return urllib2.urlopen(rt.url, body)

    return record


def _integration_test(ini='redcap.ini', section='redcap'):
    return connector(ini, section)


if __name__ == '__main__':
    c = _integration_test()
    response = c()
    pprint.pprint(response.info().headers)
    print response.read()
