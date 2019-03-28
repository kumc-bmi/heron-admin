'''redcap_connect.py -- Connect HERON users to REDCap surveys securely.
-----------------------------------------------------------------------

Configuration gives us access to the REDCap API::

  >>> print(_test_settings.inifmt('survey_xyz'))
  [survey_xyz]
  domain=js.example
  engine=redcapdb:Mock
  project_id=34
  survey_id=11
  survey_url=http://testhost/redcap-host/surveys/?s=43

  >>> set(OPTIONS) < set(_test_settings.settings().keys())
  True

  >>> io = redcap_invite.MockIO()
  >>> setup = SurveySetup(_test_settings, io.connect, io.rng)

Set up a link to survey associated with John Smith's email address::

  >>> setup('john.smith',
  ...       {'user_id': 'john.smith', 'full_name': 'John Smith'}).split('?')
  ... # doctest: +NORMALIZE_WHITESPACE
  ['http://testhost/redcap-host/surveys/',
   's=aqFVbr&full_name=John+Smith&user_id=john.smith']

Fill in some of the fields in the survey, such as `full_name` and `what_for`::

  >>> setup('john.smith',
  ...       {'multi': 'yes', 'user_id': 'john.smith',
  ...        'what_for': '2', 'full_name': 'Smith, John'},
  ...       multi=True).split('&')
  ... # doctest: +NORMALIZE_WHITESPACE
  ['http://testhost/redcap-host/surveys/?s=aqFVbr',
   'full_name=Smith%2C+John',
   'multi=yes', 'user_id=john.smith', 'what_for=2']
'''

from __future__ import print_function
import logging
from pprint import pformat
from urllib import urlencode
from urlparse import urljoin

from injector import singleton, provides, Key
from sqlalchemy.engine.base import Connectable

from ocap_file import Path
import rtconfig
import redcap_invite

log = logging.getLogger(__name__)

OPTIONS = ('survey_url', 'domain', 'survey_id')
KRandom = Key(__name__ + '.Random')


class SurveySetup(object):
    def __init__(self, rt, connect, rng, project_id=None, survey_id=None):
        self.__ss = redcap_invite.SecureSurvey(connect, rng, survey_id)
        self.domain = rt.domain
        self.base = rt.survey_url
        self.survey_id = survey_id
        self.project_id = project_id

    def __call__(self, userid, params, multi=False):
        email = '%s@%s' % (userid, self.domain)
        surveycode = self.__ss.invite(email, multi)
        assert surveycode
        params = urlencode([('s', surveycode)]
                           + sorted(params.iteritems()))
        return urljoin(self.base, '?' + params)

    def responses(self, email):
        return self.__ss.responses(email)


_test_settings = rtconfig.TestTimeOptions(dict(
    engine='redcapdb:Mock',
    survey_url='http://testhost/redcap-host/surveys/?s=43',
    domain='js.example',
    survey_id=11,
    project_id=34))


class RunTime(rtconfig.IniModule):  # pragma: nocover
    def __init__(self, ini, rng, create_engine):
        rtconfig.IniModule.__init__(self, ini)
        self.__rng = rng
        self.__create_engine = create_engine

    @singleton
    @provides((Connectable, redcap_invite.CONFIG_SECTION))
    def db_engine(self):
        opts = self.get_options(['engine'], redcap_invite.CONFIG_SECTION)
        return self.__create_engine(opts.engine, pool_recycle=3600)

    @singleton
    @provides(KRandom)
    def rng(self):
        return self.__rng

    def _setup(self, opts, connect, rng, survey_id=None):
        return SurveySetup(opts, connect, rng, survey_id=survey_id)

    def _integration_test(self, userid, fullName, stderr):
        connect = self.db_engine().connect
        rng = self.__rng
        ea_opts = [
            self.get_options(OPTIONS, section)
            for section in ['dua_survey', 'saa_survey', 'oversight_survey']]

        log.debug('opts: %s', [o.survey_id for o in ea_opts])
        [dua, saa, oversight] = [self._setup(opts, connect, rng,
                                             survey_id=opts.survey_id)
                                 for opts in ea_opts]
        try:
            for ss in [dua, saa, oversight]:
                info = ss(userid, {'email': userid + '@kumc.edu',
                                   'full_name': fullName})
                print(pformat(info), file=stderr)
        except IOError as e:
            print(e.message)
            print(e)


if __name__ == '__main__':  # pragma nocover
    def _integration_test():  # pragma: nocover
        from os.path import join as path_join, exists as path_exists
        from io import open as io_open
        from random import Random
        from sys import argv, stderr

        from sqlalchemy import create_engine

        [userid, fullName] = argv[1:3]

        logging.basicConfig(level=logging.DEBUG, stream=stderr)

        cwd = Path('.', (io_open, path_join, path_exists))

        rt = RunTime(ini=cwd / 'integration-test.ini',
                     rng=Random(), create_engine=create_engine)
        rt._integration_test(userid, fullName, stderr)

    _integration_test()
