from pprint import pformat
from urllib import urlencode
from urllib2 import HTTPError
import json
import logging
from StringIO import StringIO
from urlparse import parse_qs

from ocap_file import edef
import rtconfig

log = logging.getLogger(__name__)


_test_settings = rtconfig.TestTimeOptions(dict(
    token='sekret',
    api_url='http://redcap-host/redcap/api/',
    survey_url='http://testhost/redcap-host/surveys/?s=43',
    domain='js.example',
    survey_id=11,
    project_id=34))


def EndPoint(webcap, token):
    '''Make REDCap API endpoint with accept_json, post_json methods.

    >>> rt = _test_settings
    >>> e = EndPoint(_MockREDCapAPI(), rt.token)
    >>> e.accept_json(content='survey', action='setup',
    ...               email='john.smith@jsmith.example')
    ... # doctest: +NORMALIZE_WHITESPACE
    {u'add': 0, u'PROJECT_ID': 123, u'hash': u'f1f9',
     u'email': u'BOGUS@js.example', u'survey_id': 11}

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
        log.debug('POSTing %s to redcap at %s', pformat(data),
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
        return 'EndPoint(%s)' % webcap.fullPath()

    def record_import(data, **args):
        log.debug('import: %s', data)
        return post_json(content='record', action='import',
                         data=data, **args)

    return edef(__repr__, accept_json, post_json, record_import)


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
