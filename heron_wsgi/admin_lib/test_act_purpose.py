"""test_act_purpose -- test oversight request for ACT sponsorship

The introduction of sponsorship for ACT SHRINE exposes the way
sponsorship was granted without regard for the purpose (`what_for`) in
an oversight request.

"""

from contextlib import contextmanager
import unittest

from sqlalchemy import orm

from heron_policy import HeronRecords, PERM_STATUS
from redcap_api import _test_settings as redcap_settings
import heron_policy
import medcenter
import redcapdb


class TestActSponsorship(unittest.TestCase):
    def __init__(self, x):
        unittest.TestCase.__init__(self, x)

        [hp, mc, rcsm] = heron_policy.Mock.make([
            HeronRecords,
            medcenter.MedCenter,
            (orm.session.Session, redcapdb.CONFIG_SECTION)
        ])
        self.__heron_policy = hp
        self.__medcenter = mc
        self.__redcap_sessionmaker = rcsm

    def test_roles(self):
        """john.smith is faculty; act.user is not.
        """
        john_ctx = self._login('john.smith', PERM_STATUS).context
        self.assertTrue(self.__medcenter.idbadge(john_ctx).is_faculty())

        student_ctx = self._login('act.user', PERM_STATUS).context
        self.assertFalse(self.__medcenter.idbadge(student_ctx).is_faculty())

    unapproved_request = dict(
        user_id='john.smith',
        project_title='National search',
        date_of_expiration='2050-02-27',
        user_id_1='act.user',
    )

    def test_unapproved(self, user_id='act.user'):
        """John submits a request naming `act.user`, but it's not yet
        approved, so it does not grant access to HERON.

        """
        with _use_session(self.__redcap_sessionmaker) as s1:
            self._submit_redcap_form(s1, self.unapproved_request, '77')
        stureq = self._login(user_id, PERM_STATUS)
        self.assertFalse(stureq.context.status.sponsored)

    approved_no_purpose = dict(
        unapproved_request,
        approve_kuh='1',
        approve_kupi='1',
        approve_kumc='1',
    )

    approved_heron_query = dict(
        approved_no_purpose,
        what_for=HeronRecords.SPONSORSHIP,
    )

    def test_heron_sponsorship(self):
        """An request for HERON sponsorship grants `act.user` access to HERON query.
        """
        with _use_session(self.__redcap_sessionmaker) as s1:
            self._submit_redcap_form(s1, self.approved_heron_query, '93')
        stureq = self._login('act.user', PERM_STATUS)
        self.assertTrue(stureq.context.status.sponsored)

    approved_data_use = dict(
        approved_no_purpose,
        what_for=HeronRecords.DATA_USE,
    )

    def test_data_use(self):
        """An request for data use does not grant `act.user` access to HERON.
        """
        with _use_session(self.__redcap_sessionmaker) as s1:
            self._submit_redcap_form(s1, self.approved_data_use, '99')
        stureq = self._login('act.user', PERM_STATUS)
        self.assertFalse(stureq.context.status.sponsored)

    approved_act_sponsorship = dict(
        approved_no_purpose,
        what_for=HeronRecords.ACT_SPONSORSHIP,
    )

    def test_act_sponsorship(self):
        """An request for ACT sponsorship does not grant `act.user` access to HERON.
        """
        with _use_session(self.__redcap_sessionmaker) as s1:
            self._submit_redcap_form(s1, self.approved_act_sponsorship, '22')
        stureq = self._login('act.user', PERM_STATUS)
        self.assertFalse(stureq.context.status.sponsored)

    @classmethod
    def _submit_redcap_form(self, session, form,
                            record_id='9999',
                            project_id=redcap_settings.project_id,
                            event_id='1'):
        for field, value in form.items():
            dml = redcapdb.redcap_data.insert().values(
                project_id=project_id, event_id=event_id, record=record_id,
                field_name=field, value=value)
            session.execute(dml)

    def _login(self, uid, perm):
        req = medcenter.MockRequest()
        self.__medcenter.authenticated(uid, req)
        self.__heron_policy.grant(req.context, perm)
        return req


@contextmanager
def _use_session(session_manager):
    session = session_manager()
    try:
        yield session
    except:  # noqa
        session.rollback()
    else:
        session.commit()


if __name__ == '__main__':
    unittest.main()
