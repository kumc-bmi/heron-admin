'''noticelog -- maintain a log of email notices in a table
----------------------------------------------------------

  >>> (dr, ) = Mock.make([DecisionRecords])

Sponsorship Records
*******************

  >>> dr.sponsorships('some.one')
  [(u'6373469799195807417', u'1', u'some.one', u'john.smith', u'')]

Expired sponsorships are filtered out:

  >>> dr.sponsorships('bill.student')
  []

Projects sponsored by an investigator:

  >>> dr.sponsorships('john.smith', inv=True)
  [(u'6373469799195807417', u'1', u'john.smith', u'john.smith', u'')]

Sponsorship details:
  >>> dr.about_sponsorships('some.one')  # doctest: +NORMALIZE_WHITESPACE
  [(u'6373469799195807417', John Smith <john.smith>,
    u'Cure Warts', '')]

  >>> dr.about_sponsorships('john.smith', inv=True)
  ... # doctest: +NORMALIZE_WHITESPACE
  [(u'6373469799195807417', John Smith <john.smith>,
    u'Cure Warts', '')]

Notification of Oversight Decisions
***********************************

What decision notifications are pending?

  >>> ds = dr.oversight_decisions()
  >>> ds  # doctest: +NORMALIZE_WHITESPACE
  [(u'-565402122873664774', u'2', 3),
   (u'23180811818680005', u'1', 3),
   (u'6373469799195807417', u'1', 3)]

Get oversight details that we might want to use in composing the notification::

  >>> from pprint import pprint

  >>> pprint(dr.decision_detail(ds[0][0]))
  (John Smith <john.smith>,
   [? <bill.student>],
   {u'approve_kuh': u'2',
    u'approve_kumc': u'2',
    u'approve_kupi': u'2',
    u'date_of_expiration': u'',
    u'full_name': u'John Smith',
    u'project_title': u'Cart Blanche',
    u'user_id': u'john.smith',
    u'user_id_1': u'bill.student'})
  >>> pprint(dr.decision_detail(ds[1][0]))
  (John Smith <john.smith>,
   [? <bill.student>],
   {u'approve_kuh': u'1',
    u'approve_kumc': u'1',
    u'approve_kupi': u'1',
    u'date_of_expiration': u'1950-02-27',
    u'full_name': u'John Smith',
    u'project_title': u'Cure Polio',
    u'user_id': u'john.smith',
    u'user_id_1': u'bill.student'})
  >>> pprint(dr.decision_detail(ds[2][0]))
  (John Smith <john.smith>,
   [Some One <some.one>, ? <carol.student>],
   {u'approve_kuh': u'1',
    u'approve_kumc': u'1',
    u'approve_kupi': u'1',
    u'date_of_expiration': u'',
    u'full_name': u'John Smith',
    u'name_etc_1': u'Some One',
    u'project_title': u'Cure Warts',
    u'user_id': u'john.smith',
    u'user_id_1': u'some.one',
    u'user_id_2': u'carol.student'})

Get current email addresses of the team:

  >>> record = ds[0][0]
  >>> inv, team, _ = dr.decision_detail(record)
  >>> dr.team_email(inv.cn, [mem.cn for mem in team])
  ('john.smith@js.example', ['bill.student@js.example'])

The following table is used to log notices::

  >>> from sqlalchemy import create_engine
  >>> from sqlalchemy.schema import CreateTable
  >>> ddl = CreateTable(notice_log, bind=create_engine('sqlite://'))
  >>> print str(ddl).strip()
  ... #doctest: +NORMALIZE_WHITESPACE
  CREATE TABLE notice_log (
      id INTEGER NOT NULL,
      record VARCHAR(100),
      timestamp TIMESTAMP,
      PRIMARY KEY (id),
      FOREIGN KEY(record) REFERENCES redcap_data (record)
  )

'''

import logging
from collections import namedtuple

import injector
from injector import inject, provides
from sqlalchemy import Table, Column
from sqlalchemy.types import Integer, VARCHAR, TIMESTAMP
from sqlalchemy.schema import ForeignKey
from sqlalchemy import orm
from sqlalchemy.sql import select, func, and_

import rtconfig
import redcapdb
import medcenter
from ocap_file import Token

log = logging.getLogger(__name__)
OVERSIGHT_CONFIG_SECTION = 'oversight_survey'
KProjectId = injector.Key('ProjectId')
notice_log = Table('notice_log', redcapdb.Base.metadata,
                   Column('id', Integer, primary_key=True),
                   Column('record', VARCHAR(100),
                          ForeignKey('redcap_data.record')),
                   Column('timestamp', TIMESTAMP()),
                   schema='droctools',
                   mysql_engine='InnoDB',
                   mysql_collate='utf8_unicode_ci')


class DecisionRecords(Token):
    '''

    .. note:: At test time, let's check consistency with the data
              dictionary.

    >>> from ddict import DataDict
    >>> choices = dict(DataDict('oversight').radio('approve_kuh'))
    >>> choices[DecisionRecords.YES]
    'Yes'
    >>> choices[DecisionRecords.NO]
    'No'
    >>> len(choices)
    3

    '''

    YES = '1'
    NO = '2'
    institutions = ('kuh', 'kupi', 'kumc')

    @inject(pid=KProjectId,
            smaker=(orm.session.Session, redcapdb.CONFIG_SECTION),
            browser=medcenter.Browser,
            clock=rtconfig.Clock)
    def __init__(self, pid, smaker, browser, clock):
        self._oversight_project_id = pid
        self._browser = browser
        self._smaker = smaker
        self._clock = clock

    def sponsorships(self, uid, inv=False):
        '''Enumerate current (un-expired) sponsorships by/for uid.
        :param inv: True=by (i.e. investigator); False=for
        '''
        _d, _c, dc = _sponsor_queries(self._oversight_project_id,
                                      len(self.institutions), inv)

        # mysql work-around for
        # 1248, 'Every derived table must have its own alias'
        dc = dc.alias('mw')
        q = dc.select(and_(dc.c.candidate == uid,
                           dc.c.decision == DecisionRecords.YES)).\
                               order_by(dc.c.record)

        answers = self._smaker().execute(q).fetchall()
        min_exp = self._clock.now()
        return [ans for ans in answers
                # hmm... why not do this date comparison in the database?
                if (ans.dt_exp <= ''
                    or min_exp.isoformat() <= ans.dt_exp)]

    def about_sponsorships(self, who, inv=False):
        return [(record, inv, detail.get('project_title', ''),
                 project_description(detail))
                for record, (inv, team, detail) in [
                        (sponsorship.record,
                         self.decision_detail(sponsorship.record))
                        for sponsorship in self.sponsorships(who, inv)]]

    def oversight_decisions(self, pending=True):
        '''In order to facilitate email notification of committee
        decisions, find decisions where notification has not been sent.
        '''
        cd, who, cdwho = _sponsor_queries(self._oversight_project_id,
                                          len(self.institutions))

        # decisions without notifications
        if pending:
            nl = notice_log
            dwn = cd.outerjoin(nl).select() \
                                  .with_only_columns(cd.columns)\
                                  .where(nl.c.record == None)
        else:
            dwn = cd

        return self._smaker().execute(dwn).fetchall()

    def decision_detail(self, record, lookup=True):
        s = self._smaker()
        d = dict(redcapdb.allfields(s,
                                    self._oversight_project_id,
                                    record))
        s.close()

        def ref(user_id_n):
            cn = d[user_id_n]
            name_etc_n = user_id_n.replace('user_id_', 'name_etc_')
            name_etc = d.get(name_etc_n, '')
            fn = name_etc.split('\n')[0]
            return Ref(cn, fn, name_etc)

        inv = Ref(d['user_id'], d['full_name'], None)
        team = [ref(user_id_n)
                for user_id_n in sorted(d.keys())
                if user_id_n.startswith('user_id_')]

        return inv, team, d

    def team_email(self, inv_uid, team_uids):
        '''Get email addresses for investigator plus those team members
        that are on file.
        '''
        browser = self._browser

        def try_lookup(who):
            try:
                return browser.lookup(who)
            except KeyError:
                log.warn('no email for %s', who)
                return None

        return (browser.lookup(inv_uid).mail,
                [entry.mail
                 for entry in [try_lookup(uid) for uid in team_uids]
                 if entry and hasattr(entry, 'mail')])


def project_description(detail):
    return (detail.get('description_sponsor', None) or
            detail.get('data_use_description', ''))

ProperName = namedtuple('ProperName', ('cn', 'fn', 'name_etc'))


class Ref(ProperName):
    def __repr__(self):
        return '%s <%s>' % (self.fn or '?', self.cn)

    def full_name(self):
        return self.fn


def _sponsor_queries(oversight_project_id, parties, inv=False):
    '''
    TODO: consider a separate table of approved users, generated when
    notices are sent. include expirations (and link back to request).

      >>> from pprint import pprint
      >>> decision, candidate, cdwho = _sponsor_queries(123, 3)

      >>> print str(decision)
      ...  # doctest: +NORMALIZE_WHITESPACE
      SELECT p.record, p.value AS decision, count(*) AS count_1
      FROM
        (SELECT redcap_data.record AS record,
                redcap_data.field_name AS field_name,
                redcap_data.value AS value
                FROM redcap_data
                WHERE redcap_data.project_id = :project_id_1) AS p
      WHERE p.field_name LIKE :field_name_1 GROUP BY p.record, p.value
      HAVING count(*) = :count_2

      >>> pprint(decision.compile().params)
      {u'count_2': 3, u'field_name_1': 'approve_%', u'project_id_1': 123}


      >>> print str(candidate)
      ...  # doctest: +NORMALIZE_WHITESPACE
      SELECT p.record, p.value AS userid
      FROM
        (SELECT redcap_data.record AS record,
                redcap_data.field_name AS field_name,
                redcap_data.value AS value
         FROM redcap_data
         WHERE redcap_data.project_id = :project_id_1) AS p
      WHERE p.field_name LIKE :field_name_1

      >>> print str(cdwho)
      ...  # doctest: +NORMALIZE_WHITESPACE
      SELECT cd_record AS record,
      cd_decision AS decision,
      who_userid AS candidate,
      sponsor_userid AS sponsor,
      expire_dt_exp AS dt_exp
        FROM
            (SELECT cd.record AS cd_record,
            cd.decision AS cd_decision,
            cd.count_1 AS cd_count_1,
            who.record AS who_record,
            who.userid AS who_userid,
            sponsor.record AS sponsor_record,
            sponsor.userid AS sponsor_userid,
            expire.record AS expire_record,
            expire.dt_exp AS expire_dt_exp
            FROM
                (SELECT p.record AS record,
                p.value AS decision, count(*) AS count_1
                FROM
                    (SELECT redcap_data.record AS record,
                    redcap_data.field_name AS field_name,
                    redcap_data.value AS value
                    FROM redcap_data
                    WHERE redcap_data.project_id = :project_id_1) AS p
                WHERE p.field_name LIKE :field_name_1 GROUP
                BY p.record, p.value
                HAVING count(*) = :count_2) AS cd
            JOIN
                (SELECT p.record AS record,
                p.value AS userid
                FROM
                    (SELECT redcap_data.record AS record,
                    redcap_data.field_name AS field_name,
                    redcap_data.value AS value
                    FROM redcap_data
                    WHERE redcap_data.project_id = :project_id_1) AS p
                WHERE p.field_name LIKE :field_name_2) AS who
            ON who.record = cd.record
            JOIN
                (SELECT p.record AS record, p.value AS userid
                FROM
                    (SELECT redcap_data.record AS record,
                    redcap_data.field_name AS field_name,
                    redcap_data.value AS value
                    FROM redcap_data
                    WHERE redcap_data.project_id = :project_id_1) AS p
                WHERE p.field_name = :field_name_3) AS sponsor
            ON sponsor.record = cd.record
            LEFT OUTER JOIN
                (SELECT p.record AS record,
                p.value AS dt_exp
                FROM
                    (SELECT redcap_data.record AS record,
                    redcap_data.field_name AS field_name,
                    redcap_data.value AS value
                    FROM redcap_data
                    WHERE redcap_data.project_id = :project_id_1) AS p
                WHERE p.field_name = :field_name_4) AS expire
            ON expire.record = cd.record) AS cdwho

      >>> pprint(cdwho.compile().params)
      {u'count_2': 3,
       u'field_name_1': 'approve_%',
       u'field_name_2': 'user_id_%',
       u'field_name_3': 'user_id',
       u'field_name_4': 'date_of_expiration',
       u'project_id_1': 123}

    '''
    # grumble... sql in python clothing
    # but for this price, we can run it on sqlite for testing as well as mysql
    # and sqlalchemy will take care of the bind parameter syntax
    rdc = redcapdb.redcap_data.c
    proj = select([rdc.record, rdc.field_name, rdc.value]).where(
        rdc.project_id == oversight_project_id).alias('p')

    # committee decisions
    decision = select((proj.c.record,
                       proj.c.value.label('decision'),
                       func.count())).where(
        proj.c.field_name.like('approve_%')).\
             group_by(proj.c.record,
                      proj.c.value).having(
                 func.count() == parties).alias('cd')

    # todo: consider combining record, event, project_id into one attr
    candidate = select((proj.c.record,
                        proj.c.value.label('userid'))).where(
        proj.c.field_name.like('user_id' if inv else 'user_id_%')).alias('who')

    sponsor = select((proj.c.record,
                        proj.c.value.label('userid'))).where(
        proj.c.field_name == 'user_id').alias('sponsor')

    dt_exp = select((proj.c.record,
                     proj.c.value.label('dt_exp'))).where(
        proj.c.field_name == 'date_of_expiration').alias('expire')

    j = decision.join(candidate,
                      candidate.c.record == decision.c.record).\
                      join(sponsor,
                      sponsor.c.record == decision.c.record).\
                          outerjoin(dt_exp,
                                    dt_exp.c.record == decision.c.record).\
                                        alias('cdwho').select()

    cdwho = j.with_only_columns((j.c.cd_record.label('record'),
                                 j.c.cd_decision.label('decision'),
                                 j.c.who_userid.label('candidate'),
                                 j.c.sponsor_userid.label('sponsor'),
                                 j.c.expire_dt_exp.label('dt_exp')))

    return decision, candidate, cdwho


def migrate_decisions(ds, outfp):
    import csv

    logging.basicConfig(level=logging.DEBUG)
    log = logging.getLogger(__name__)
    out = csv.writer(outfp)

    # schema
    out.writerow(('record', 'decision',
                  'inv', 'mem', 'expiration',
                  'purpose', 'title', 'description'))

    log.debug('about to query for all decisions...')
    data = list(ds.oversight_decisions(pending=False))
    log.debug('got %s decisions', len(data))
    for record, decision, qty in data:
        log.debug('about to get record %s ...', record)
        inv, team, detail = ds.decision_detail(record, lookup=False)
        log.debug('... got %s fields from record %s', len(detail), record)
        for mem in team:
            out.writerow((record, decision, inv, mem,
                          detail.get('date_of_expiration', ''),
                          detail.get('what_for'),
                          detail.get('project_title', ''),
                          detail.get('description_sponsor', '')))

    raise NotImplementedError


class Mock(injector.Module, rtconfig.MockMixin):
    @provides(KProjectId)
    def project_id(self):
        import redcap_connect
        return redcap_connect._test_settings.project_id

    @provides(rtconfig.Clock)
    def clock(self):
        return rtconfig.MockClock()

    @classmethod
    def mods(cls):
        import medcenter
        return redcapdb.Mock.mods() + medcenter.Mock.mods() + [cls()]


class RunTime(rtconfig.IniModule):  # pragma nocover
    @provides(KProjectId)
    def project_id(self):
        rt = self.get_options(['project_id'], OVERSIGHT_CONFIG_SECTION)
        return rt.project_id

    @provides(rtconfig.Clock)
    def real_time(self):
        import datetime
        return datetime.datetime

    @classmethod
    def mods(cls, ini):
        return [im
                for m in (redcapdb, medcenter)
                for im in m.RunTime.mods(ini)] + [cls(ini)]


def _integration_test():  # pragma nocover
    import sys
    (ds, ) = RunTime.make(None, [DecisionRecords])

    if '--migrate' in sys.argv:
        migrate_decisions(ds, sys.stdout)
        raise SystemExit(0)
    elif '--sponsorships' in sys.argv:
        who = sys.argv[2]
        print ds.about_sponsorships(who)

    print "pending notifications:", ds.oversight_decisions()


if __name__ == '__main__':  # pragma nocover
    _integration_test()
