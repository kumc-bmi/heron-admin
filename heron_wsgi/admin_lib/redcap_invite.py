'''redcap_invite -- forgery-resistant REDCap surveys

Suppose the System Access Agreement is survey 11:

    >>> io = MockIO()
    >>> saa = SecureSurvey(io.connect, io.rng, 11)

Has big.wig responded? When?

    >>> saa.response('big.wig@js.example')
    (u'3253004250825796194', datetime.datetime(2011, 8, 26, 0, 0))

Bob follows the system access survey link, so we generate a survey
invitation hash just for him:

    >>> print(saa.invite('bob@js.example'))
    qTwAVx

ISSUE: REDCap logging?

If he follows the link again, we find the invitation we already made
for him:

    >>> print(saa.invite('bob@js.example'))
    qTwAVx

He hasn't responded yet:
    >>> saa.response('bob@js.example')

'''

from __future__ import print_function
from ConfigParser import SafeConfigParser
import logging

from sqlalchemy import and_, select

import redcapdb

log = logging.getLogger(__name__)
CONFIG_SECTION = 'survey_invite'

Nonce = str


class SecureSurvey(object):
    def __init__(self, connect, rng, survey_id):
        # type: (Callable[..., Connection], Random_T, int) -> None
        self.__connect = connect
        self.__rng = rng
        self.survey_id = survey_id

    @classmethod
    def _config(cls, config_fp, config_filename, survey_section,
                db_section='survey_invite'):
        # type: (TextIO, str, str, str) -> Tuple[str, str]
        config = SafeConfigParser()
        config.readfp(config_fp, config_filename)
        survey_id = config.getint(survey_section, 'survey_id')
        db_url = config.get('survey_invite', 'engine')
        return survey_id, db_url

    def invite(self, email,
               tries=5):
        # type: (str, int) -> str
        '''
        :return: hash for participant
        '''
        conn = self.__connect()
        pt, find = self._invitation_q(self.survey_id)

        found = conn.execute(
            find.where(pt.c.participant_email == email)).fetchone()
        if found:
            (nonce,) = found
            return nonce

        failure = None
        for attempt in range(tries):
            try:
                nonce = self.generateRandomHash()
                with conn.begin():
                    clash = conn.execute(
                        find.where(pt.c.hash == nonce)).fetchone()
                    if clash:
                        continue
                    add = self._invite_dml(self.survey_id, email, nonce)
                    conn.execute(add)
                    return nonce
            except IOError as failure:
                pass
        else:
            raise failure

    @classmethod
    def _invitation_q(cls, survey_id):
        # type: (int) -> Operation
        '''
        :return: participants table, partial query

        >>> _t, q = SecureSurvey._invitation_q(11)
        >>> print(q)
        ... # doctest: +NORMALIZE_WHITESPACE
        SELECT p.hash
        FROM redcap_surveys_participants AS p
        WHERE p.survey_id = :survey_id_1

        '''
        pt = redcapdb.redcap_surveys_participants.alias('p')
        return pt, select([pt.c.hash]).where(
            and_(pt.c.survey_id == survey_id))

    @classmethod
    def _invite_dml(cls, survey_id, email, nonce,
                    part_ident='',  # not known yet. (per add_participants.php)
                    event_id=None):
        # type: (int, str) -> Operation
        '''

        design based on add_participants.php from REDCap 4.14.5

        >>> op = SecureSurvey._invite_dml(11, 'x@y', 'p1', 'sekret')
        >>> print(op)
        ... # doctest: +NORMALIZE_WHITESPACE
        INSERT INTO redcap_surveys_participants
          (survey_id, event_id, hash, participant_email,
           participant_identifier)
        VALUES (:survey_id, :event_id, :hash, :participant_email,
           :participant_identifier)
        '''
        # type: (str, str, str, Nonce, Opt[str]) -> Operation
        pt = redcapdb.redcap_surveys_participants
        return pt.insert().values(
            survey_id=survey_id,
            event_id=event_id,
            participant_email=email,
            participant_identifier=part_ident,
            hash=nonce)

    def generateRandomHash(self):
        # type: () -> str
        '''

        based on redcap_v4.7.0/Config/init_functions.php: generateRandomHash

        >>> io = MockIO()
        >>> s = SecureSurvey(None, io.rng, 11)
        >>> [s.generateRandomHash(), s.generateRandomHash()]
        ['qTwAVx', 'jpMZfX']
        '''
        rng = self.__rng
        cs = list("abcdefghijkmnopqrstuvwxyzABCDEFGHIJKLMNPQRSTUVWXYZ23456789")
        rng.shuffle(cs)
        lr = cs[:6]
        rng.shuffle(lr)
        return ''.join(lr)

    def response(self, email):
        # type: str -> Opt[Tuple(str, datetime)]
        conn = self.__connect()
        q = self._response_q(email, self.survey_id)
        return conn.execute(q).fetchone()

    @classmethod
    def _response_q(cls, email, survey_id):
        # type: (str, int) -> Operation
        '''
        >>> q = SecureSurvey._response_q('xyz@abc', 12)
        >>> print(q)
        ... # doctest: +NORMALIZE_WHITESPACE
        SELECT r.record, r.completion_time
        FROM redcap_surveys_response AS r, redcap_surveys_participants AS p
        WHERE r.participant_id = p.participant_id
          AND p.participant_email = :participant_email_1
          AND p.survey_id = :survey_id_1

        '''
        r = redcapdb.redcap_surveys_response.alias('r')
        p = redcapdb.redcap_surveys_participants.alias('p')
        return select([r.c.record, r.c.completion_time]).where(
            and_(r.c.participant_id == p.c.participant_id,
                 p.c.participant_email == email, p.c.survey_id == survey_id))


class MockIO(object):
    def __init__(self):
        from random import Random
        self.rng = Random(1)
        self.connect = redcapdb.Mock.engine().connect


def _integration_test(argv, io_open, Random, create_engine,
                      survey_section='saa_survey',
                      config_file='integration-test.ini'):  # pragma: nocover
    logging.basicConfig(level=logging.DEBUG)

    email_addr = argv[1]
    survey_id, db_url = SecureSurvey._config(
        io_open(config_file), config_file, survey_section)

    saa = SecureSurvey(create_engine(db_url).connect, Random(), survey_id)
    _explore(email_addr, saa)


def _explore(email_addr, saa):
    log.info('response to survey %s from %s?', saa.survey_id, email_addr)
    response = saa.response(email_addr)
    if response:
        record, when = response
        log.info('record %s completed %s', record, when)
    else:
        log.info('none')

    log.info('inviting %s', email_addr)
    part_id = saa.invite(email_addr)
    log.info('hash: %s', part_id)


if __name__ == '__main__':
    def _script():
        from random import Random
        from sys import argv
        from io import open as io_open

        import sqlalchemy
        _integration_test(argv, io_open, Random,
                          sqlalchemy.create_engine)

    _script()
