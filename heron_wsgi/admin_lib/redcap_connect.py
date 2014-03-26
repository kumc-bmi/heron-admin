'''redcap_connect.py -- Connect HERON users to REDCap surveys securely.
-----------------------------------------------------------------------

Configuration gives us access to the REDCap API::

  >>> print _test_settings.inifmt('survey_xyz')
  [survey_xyz]
  api_url=http://redcap-host/redcap/api/
  domain=example.edu
  project_id=34
  survey_id=11
  survey_url=http://testhost/redcap-host/surveys/?s=43
  token=sekret

  >>> set(OPTIONS) < set(_test_settings.settings().keys())
  True

  >>> setup = SurveySetup(_test_settings,
  ...                     EndPoint(_MockREDCapAPI(), _test_settings.token))

Set up a link to survey associated with John Smith's email address::

  >>> setup('john.smith',
  ...       {'user_id': 'john.smith', 'full_name': 'John Smith'}).split('?')
  ... # doctest: +NORMALIZE_WHITESPACE
  ['http://testhost/redcap-host/surveys/',
   's=f1f9&full_name=John+Smith&user_id=john.smith']

Fill in some of the fields in the survey, such as `full_name` and `what_for`::

  >>> setup('john.smith',
  ...       {'multi': 'yes', 'user_id': 'john.smith',
  ...        'what_for': '2', 'full_name': 'Smith, John'},
  ...       multi=True).split('&')
  ... # doctest: +NORMALIZE_WHITESPACE
  ['http://testhost/redcap-host/surveys/?s=f1f9',
   'full_name=Smith%2C+John',
   'multi=yes', 'user_id=john.smith', 'what_for=2']
'''

import json
from StringIO import StringIO
import logging
import pprint
from urllib import urlencode
from urlparse import urljoin, parse_qs
from urllib2 import HTTPError

import rtconfig
from ocap_file import edef, WebPostable

log = logging.getLogger(__name__)

OPTIONS = ('token', 'api_url', 'survey_url', 'domain', 'survey_id')


def EndPoint(webcap, token):
    '''Make REDCap API endpoint with accept_json, post_json methods.

    >>> rt = _test_settings
    >>> e = EndPoint(_MockREDCapAPI(), rt.token)
    >>> e.accept_json(content='survey', action='setup',
    ...               email='john.smith@jsmith.example')
    ... # doctest: +NORMALIZE_WHITESPACE
    {u'add': 0, u'PROJECT_ID': 123, u'hash': u'f1f9',
     u'email': u'BOGUS@example.edu', u'survey_id': 11}

    >>> e.record_import([{'field': 'value'}])
    '{}'
    '''
    def accept_json(content, **args):
        body = _request(content, format='json', **args)
        try:
            ans = json.loads(body)
        except ValueError as ex:
            log.error('REDCap API answer not JSON: %s', body, exc_info=ex)
            raise
        return ans

    def post_json(content, data, **args):
        log.debug('POSTing %s to redcap at %s', pprint.pformat(data),
                  webcap.fullPath())
        return _request(content=content, format='json',
                        data=json.dumps(data), **args)

    def _request(content, format, **args):
        params = dict(args, token=token, content=content, format=format)
        try:
            res = webcap.post(urlencode(params))
        except HTTPError as ex:
            log.error('REDCap error body: %s', ex.read())
            raise
        return res.read()

    def __repr__():
        return 'redcap_connect.EndPoint(%s)' % webcap.fullPath()

    def record_import(data, **args):
        log.debug('import: %s', data)
        return post_json(content='record', action='import',
                         data=data, **args)

    return edef(__repr__, accept_json, post_json, record_import)


class SurveySetup(object):
    def __init__(self, rt, endpoint, project_id=None, survey_id=None):
        self.__endpoint = endpoint
        self.domain = rt.domain
        self.base = rt.survey_url
        self.survey_id = survey_id
        self.project_id = project_id

    def __call__(self, userid, params, multi=False):
        redcap = self.__endpoint
        ans = redcap.accept_json(content='survey', action='setup',
                                 multi='yes' if multi else 'no',
                                 email='%s@%s' % (userid, self.domain))
        surveycode = ans['hash']
        params = urlencode([('s', surveycode)]
                           + sorted(params.iteritems()))
        return urljoin(self.base, '?' + params)


_test_settings = rtconfig.TestTimeOptions(dict(
    token='sekret',
    api_url='http://redcap-host/redcap/api/',
    survey_url='http://testhost/redcap-host/surveys/?s=43',
    domain='example.edu',
    survey_id=11,
    project_id=34))


class _MockREDCapAPI(object):
    '''
    .. todo:: check for correct token.
    '''
    addr = _test_settings.api_url

    def post(self, body):
        params = parse_qs(body)
        if 'action' not in params:
            raise IOError('action param missing: ' + str(params))
        return self.dispatch(params)

    def dispatch(self, params):
        if 'setup' in params['action']:
            return self.service_setup(params)
        elif 'import' in params['action']:
            return self.service_import(params)
        else:
            raise IOError(params['action'])

    def service_setup(self, params):
        from hashlib import md5
        h = md5(self.addr).hexdigest()[-4:]
        out = {'PROJECT_ID': 123,
               'add': 0,
               'survey_id': _test_settings.survey_id,
               'hash': h,
               'email': u'BOGUS@%s' % _test_settings.domain}
        return StringIO(json.dumps(out))

    def service_import(self, params):
        return StringIO(json.dumps({}))

    def fullPath(self):
        return self.addr


class RunTime(rtconfig.IniModule):  # pragma: nocover
    @classmethod
    def integration_test(cls):
        from urllib2 import build_opener, Request

        mod = cls(None)
        sopts = mod.get_options(OPTIONS, 'saa_survey')
        oopts = mod.get_options(OPTIONS, 'oversight_survey')
        redcap = WebPostable(sopts.api_url, build_opener(), Request)
        s1 = SurveySetup(sopts, EndPoint(redcap, sopts.token))
        s2 = SurveySetup(oopts, EndPoint(redcap, oopts.token))
        return s1, s2

    @classmethod
    def endpoint(cls, mod, section, extra=()):
        from urllib2 import build_opener, Request

        opts = mod.get_options(OPTIONS + extra, section)
        webcap = WebPostable(opts.api_url, build_opener(), Request)
        return opts, EndPoint(webcap, opts.token)


def _test_multi_use(c, uid, full_name):  # pragma: nocover
    '''Test that a user can use the same survey to make multiple requests.
    '''
    from urllib2 import urlopen

    params = {'email': uid + '@kumc.edu', 'full_name': full_name}
    addr1 = c(uid, params, multi=True)

    content1 = urlopen(addr1).read()
    if 'already' in content1:
        raise ValueError('form for 1st request says ...already...')

    print "@@ The next couple tests are kinda broken."

    addr2 = c(uid, params, multi=True)
    if addr2 == addr1:
        raise ValueError('2nd request has same address as 1st: %s = %s' % (
            addr1, addr2))

    content2 = urlopen(addr2).read()
    if 'already' in content2:
        raise ValueError('form for 2nd request says ...already...')


def _integration_test():  # pragma: nocover
    import sys
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

    #@@ _test_multi_use(c2, userid, fullName)


if __name__ == '__main__':  # pragma nocover
    _integration_test()
