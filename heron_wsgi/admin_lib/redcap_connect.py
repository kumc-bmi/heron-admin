'''redcap_connect.py -- Connect HERON users to REDCap surveys.

  >>> print _test_settings.inifmt('survey_xyz')
  [survey_xyz]
  api_url=http://redcap-host/redcap/api/
  domain=example.edu
  executives=big.wig
  project_id=34
  survey_id=11
  survey_url=http://bmidev1/redcap-host/surveys/?s=43
  token=sekret

  >>> set(OPTIONS) < set(_test_settings.settings().keys())
  True

  >>> setup = survey_setup(_test_settings, _TestUrlOpener())
  >>> setup('john.smith',
  ...       {'user_id': 'john.smith', 'full_name': 'John Smith'}).split('?')
  ... # doctest: +NORMALIZE_WHITESPACE
  ['http://bmidev1/redcap-host/surveys/',
   's=8074&full_name=John+Smith&user_id=john.smith']


'''
import json
import logging
import pprint
import sys
import urllib
from urlparse import urljoin

import rtconfig
from sealing import EDef


log = logging.getLogger(__name__)


OPTIONS=('token', 'api_url', 'survey_url', 'domain', 'survey_id')

def survey_setup(rt, urlopener):
    proxy = endPoint(urlopener, rt.api_url, rt.token)
    domain = rt.domain

    def setup(userid, params, multi=False, ans_kludge=None):
        ans = proxy.accept_json(content='survey', action='setup',
                                multi='yes' if multi else 'no',
                                email='%s@%s' % (userid, domain))
        surveycode = ans['hash']
        if ans_kludge:
            ans_kludge(ans)
        params = urllib.urlencode([('s', surveycode)]
                                  + sorted(params.iteritems()))
        return urljoin(rt.survey_url, '?' + params)

    return setup


def endPoint(ua, addr, token):
    '''Make REDCap API endpoint with accept_json, post_csv methods.

    >>> rt = _test_settings
    >>> e = endPoint(_TestUrlOpener(), rt.api_url, rt.token)
    >>> e.accept_json(content='survey', action='setup',
    ...               email='john.smith@jsmith.example')
    ... # doctest: +NORMALIZE_WHITESPACE
    {u'add': 0, u'PROJECT_ID': 123, u'hash': u'8074',
     u'email': u'BOGUS@example.edu', u'survey_id': 11}

    >>> e.record_import([{'field': 'value'}])
    {}
    '''

    def record_import(data, **args):
        return accept_json(content='record', action='import', data=data, **args)

    def accept_json(content, **args):
        ans = json.loads(_request(content, format='json', **args))
        log.debug('REDCap API JSON answer: %s', ans)
        return ans

    def post_json(content, data, **args):
        log.debug('POSTing %s to redcap at %s', pprint.pformat(data), addr)
        return _request(content=content, format='json',
                        data=json.dumps(data), **args)

    def _request(content, format, **args):
        params = dict(args, token=token, content=content, format=format)
        return ua.open(addr, urllib.urlencode(params)).read()

    return EDef(accept_json=accept_json,
                post_json=post_json,
                record_import=record_import)


class _TestUrlOpener(object):
    def open(self, addr, body):
        import urlparse  # lazy
        params = urlparse.parse_qs(body)
        if 'action' not in params:
            raise IOError('action param missing: ' + str(params))
        if 'setup' in params['action']:
            h = hex(abs(hash(addr)))[-4:]
            out = {'PROJECT_ID': 123,
                   'add': 0,
                   'survey_id': _test_settings.survey_id,
                   'hash': h,
                   'email': u'BOGUS@%s' % _test_settings.domain}
            return _TestResponse(out)
        elif 'import' in params['action']:
            out = {}
            return _TestResponse(out)
        else:
            raise ValueError, params['action']


class _TestResponse(object):
    def __init__(self, d):
        self._d = d

    def read(self):
        return json.dumps(self._d)

_test_settings = rtconfig.TestTimeOptions(dict(
    token='sekret',
    api_url='http://redcap-host/redcap/api/',
    survey_url='http://bmidev1/redcap-host/surveys/?s=43',
    domain='example.edu',
    executives='big.wig',
    survey_id=11,
    project_id=34))


class RunTime(rtconfig.IniModule):
    def configure(self, binder):
        self.bind_options(binder, OPTIONS, 'saa_survey')
        self.bind_options(binder, OPTIONS, 'oversight_survey')

    @classmethod
    def integration_test(cls):
        (sopts, oopts) = cls.make(None, [(rtconfig.Options, 'saa_survey'),
                                         (rtconfig.Options, 'saa_survey')])
        ua = urllib.URLopener()
        s1 = survey_setup(sopts, ua)
        s2 = survey_setup(oopts, ua)
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
    logging.basicConfig(level=logging.DEBUG, stream=sys.stderr)

    userid, fullName = sys.argv[1:3]
    c1, c2 = RunTime.integration_test()
    try:
        pprint.pprint(c1(userid, {'email': userid + '@kumc.edu',
                                  'full_name': fullName}))
        pprint.pprint(c2(userid, {'email': userid + '@kumc.edu',
                                  'full_name': fullName}))
    except IOError, e:
        print e.message
        print e

    _test_multi_use(c2, userid, fullName, urllib.URLopener())


if __name__ == '__main__':  # pragma nocover
    _test_main()
