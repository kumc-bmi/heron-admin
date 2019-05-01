'''redcap_invite -- forgery-resistant REDCap surveys

Suppose the System Access Agreement is survey 11:

    >>> io = MockIO()
    >>> saa = SecureSurvey(io.connect, io.rng, 11)

Has big.wig responded? When?

    >>> saa.responses('big.wig@js.example')
    [(u'3253004250825796194', datetime.datetime(2011, 8, 26, 0, 0))]

Bob follows the system access survey link, so we generate a survey
invitation hash just for him:

    >>> print(saa.invite('bob@js.example'))
    aqFVbr

ISSUE: REDCap logging?

If he follows the link again, we find the invitation we already made
for him:

    >>> print(saa.invite('bob@js.example'))
    aqFVbr

He hasn't responded yet:
    >>> saa.responses('bob@js.example')
    []

'''

from __future__ import print_function
from ConfigParser import SafeConfigParser
from random import Random as Random_T
import datetime
import logging
from typing import Callable, List, Optional as Opt, TextIO, Tuple

from sqlalchemy import and_, select
from sqlalchemy.engine import Connection  # type only
from sqlalchemy.exc import OperationalError
from sqlalchemy.sql.expression import Executable

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
               multi=False,
               tries=5):
        # type: (str, int) -> str
        '''
        :return: hash for participant
        '''
        conn = self.__connect()
        event_id = conn.execute(self._event_q(self.survey_id)).scalar()
        pt, find = self._invitation_q(self.survey_id, event_id, multi)

        found = conn.execute(
            find.where(pt.c.participant_email == email)).fetchone()
        if found:
            (nonce,) = found
            assert nonce
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
                    add = self._invite_dml(
                        self.survey_id, email, nonce, event_id)
                    conn.execute(add)
                    return nonce
            except IOError as failure:
                pass
        else:
            raise (failure or IOError('cannot find surveycode:' + nonce))

    @classmethod
    def _invitation_q(cls, survey_id, event_id,
                      multi=False):
        '''
        :return: participants table, partial query

        >>> _t, q = SecureSurvey._invitation_q(11, 1)
        >>> print(q)
        ... # doctest: +NORMALIZE_WHITESPACE
        SELECT p.hash
        FROM redcap_surveys_participants AS p
        WHERE p.survey_id = :survey_id_1
          AND p.event_id = :event_id_1
          AND p.hash > :hash_1

        >>> _t, q = SecureSurvey._invitation_q(11, 1, multi=True)
        >>> print(q)
        ... # doctest: +NORMALIZE_WHITESPACE
        SELECT p.hash
        FROM redcap_surveys_participants AS p
        LEFT OUTER JOIN redcap_surveys_response AS r
          ON p.participant_id = r.participant_id
        WHERE r.participant_id IS NULL
          AND p.hash > :hash_1
          AND p.event_id = :event_id_1
          AND p.survey_id = :survey_id_1
        LIMIT :param_1

        '''
        pt = redcapdb.redcap_surveys_participants.alias('p')
        if multi:
            rt = redcapdb.redcap_surveys_response.alias('r')
            return pt, (select([pt.c.hash])
                        .select_from(pt.join(
                            rt, pt.c.participant_id == rt.c.participant_id,
                            isouter=True))
                        .where(and_(rt.c.participant_id == None,  # noqa
                                    pt.c.hash > '',
                                    pt.c.event_id == event_id,
                                    pt.c.survey_id == survey_id))
                        .limit(1))
        return pt, select([pt.c.hash]).where(
            and_(pt.c.survey_id == survey_id,
                 pt.c.event_id == event_id,
                 pt.c.hash > ''))

    @classmethod
    def _invite_dml(cls, survey_id, email, nonce, event_id,
                    # not known yet. (per add_participants.php)
                    part_ident=''):
        # type: (int, str) -> Executable
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
        # type: (str, str, str, Nonce, Opt[str]) -> Executable
        pt = redcapdb.redcap_surveys_participants
        return pt.insert().values(
            survey_id=survey_id,
            event_id=event_id,
            participant_email=email,
            participant_identifier=part_ident,
            hash=nonce)

    @classmethod
    def _event_q(cls, survey_id):
        # type: (int) -> Executable
        '''
        >>> print(SecureSurvey._event_q(10))
        ... # doctest: +NORMALIZE_WHITESPACE
        SELECT redcap_events_metadata.event_id
        FROM redcap_surveys
        JOIN redcap_events_arms
          ON redcap_surveys.project_id = redcap_events_arms.project_id
        JOIN redcap_events_metadata
          ON redcap_events_metadata.arm_id = redcap_events_arms.arm_id
        WHERE redcap_surveys.survey_id = :survey_id_1
        '''
        srv = redcapdb.redcap_surveys
        arm = redcapdb.redcap_events_arms
        evt = redcapdb.redcap_events_metadata
        return (select([evt.c.event_id])
                .select_from(
                    srv.join(arm, srv.c.project_id == arm.c.project_id)
                .join(evt, evt.c.arm_id == arm.c.arm_id))
                .where(srv.c.survey_id == survey_id))

    def generateRandomHash(self,
                           hash_length=6):
        # type: () -> str
        '''
        based on redcap_v4.7.0/Config/init_functions.php: generateRandomHash

        >>> io = MockIO()
        >>> s = SecureSurvey(None, io.rng, 11)
        >>> [s.generateRandomHash(), s.generateRandomHash()]
        ['aqFVbr', 'akvfqA']

        TODO: increase default to 10 as in redcap 8
        '''
        rng = self.__rng
        cs = list("abcdefghijkmnopqrstuvwxyzABCDEFGHIJKLMNPQRSTUVWXYZ23456789")
        rng.shuffle(cs)
        lr = cs[:hash_length]
        rng.shuffle(lr)
        return ''.join(lr)

    def responses(self, email,
                  max_retries=10,
                  known_record_id='767',
                  known_sig_time=datetime.datetime(2017, 1, 25, 8, 55, 10)):
        '''Find responses to this survey.

        To work around persistent problems connecting to a
        REDCap DB for the system access survey, this method
        tries `max_retries` to connect and then returns a
        known survey record rather than failing:

        >>> from random import Random
        >>> predictable = Random(1)
        >>> def lose(*argv):
        ...     raise OperationalError('select...', {}, None)
        >>> ss = SecureSurvey(connect=lose, rng=predictable, survey_id=93)
        >>> ss.responses('daffy@walt.disney')
        ['767', datetime.datetime(2017, 1, 25, 8, 55, 10)]

        '''
        # type: (str) -> List[Tuple(str, datetime)]
        retryCount = max_retries

        while retryCount > 0:
            try:
                # Attempt Connection To REDCap DB
                conn = self.__connect()
            except OperationalError:
                log.info(
                    'MySQL Connection Failed, trying {0} more times...'.format(
                        max_retries - retryCount))
                retryCount = retryCount - 1
            else:
                event_id = conn.execute(self._event_q(self.survey_id)).scalar()
                q = self._response_q(email, self.survey_id, event_id)
                timestamp = conn.execute(q).fetchall()
                return timestamp

        if retryCount == 0:
            log.warn('Connect failed! Making up data for {0}'.format(email))
            eventResponse = (known_record_id, known_sig_time)

        # placing tuple in list, to follow the original comment
        # (line 2 of this method)
        return list(eventResponse)

    @classmethod
    def _response_q(cls, email, survey_id, event_id):
        # type: (str, int, int) -> Executable
        '''
        >>> q = SecureSurvey._response_q('xyz@abc', 12, 7)
        >>> print(q)
        ... # doctest: +NORMALIZE_WHITESPACE
        SELECT r.record, r.completion_time
        FROM redcap_surveys_response AS r, redcap_surveys_participants AS p
        WHERE r.participant_id = p.participant_id
          AND p.participant_email = :participant_email_1
          AND p.survey_id = :survey_id_1
          AND p.event_id = :event_id_1
        '''
        r = redcapdb.redcap_surveys_response.alias('r')
        p = redcapdb.redcap_surveys_participants.alias('p')
        return select([r.c.record, r.c.completion_time]).where(
            and_(r.c.participant_id == p.c.participant_id,
                 p.c.participant_email == email,
                 p.c.survey_id == survey_id,
                 p.c.event_id == event_id))


class MockIO(object):
    def __init__(self):
        # random.Random is not portable between cpython and jython :-/
        self.rng = self
        self._rng_state = 7
        self.connect = redcapdb.Mock.engine().connect

    def shuffle(self, items):
        n = (self._rng_state * 2 + 1) % 101
        self._rng_state = n
        n = n % len(items) or len(items)
        items[:] = [it
                    for k in range(n)
                    for it in items[k % n::n]]


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
    response = saa.responses(email_addr)
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
