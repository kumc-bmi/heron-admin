'''noticelog -- maintain a log of email notices in a table
----------------------------------------------------------

  >>> (dr, ) = Mock.make([DecisionRecords])

Sponsorship Records
*******************

  >>> dr.sponsorships('bill.student')
  [(u'23180811818680005', u'1', u'bill.student', u'1950-02-27')]

Notification of Oversight Decisions
***********************************

What decision notifications are pending?

  >>> ds = dr.oversight_decisions()
  >>> ds  # doctest: +NORMALIZE_WHITESPACE
  [(u'-565402122873664774', u'2', 3),
   (u'23180811818680005', u'1', 3),
   (u'6373469799195807417', u'1', 3)]

Get details that we might want to use in composing the notification::

  >>> from pprint import pprint
  >>> for record, decision, qty in ds:
  ...    pprint(dr.decision_detail(record))
  (John Smith <john.smith@js.example>,
   [Bill Student <bill.student@js.example>],
   {u'approve_kuh': u'2',
    u'approve_kumc': u'2',
    u'approve_kupi': u'2',
    u'date_of_expiration': u'',
    u'full_name': u'John Smith',
    u'project_title': u'Cart Blanche',
    u'user_id': u'john.smith',
    u'user_id_1': u'bill.student'})
  (John Smith <john.smith@js.example>,
   [Bill Student <bill.student@js.example>],
   {u'approve_kuh': u'1',
    u'approve_kumc': u'1',
    u'approve_kupi': u'1',
    u'date_of_expiration': u'1950-02-27',
    u'full_name': u'John Smith',
    u'project_title': u'Cure Polio',
    u'user_id': u'john.smith',
    u'user_id_1': u'bill.student'})
  (John Smith <john.smith@js.example>,
   [Some One <some.one@js.example>, Carol Student <carol.student@js.example>],
   {u'approve_kuh': u'1',
    u'approve_kumc': u'1',
    u'approve_kupi': u'1',
    u'date_of_expiration': u'',
    u'full_name': u'John Smith',
    u'project_title': u'Cure Warts',
    u'user_id': u'john.smith',
    u'user_id_1': u'some.one',
    u'user_id_2': u'carol.student'})


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


class DecisionRecords(object):
    '''

    .. note:: At test time, let's check consistency with the data
              dictionary.

    >>> choices = dict(_DataDict('oversight').radio('approve_kuh'))
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
            browser=medcenter.Browser)
    def __init__(self, pid, smaker, browser):
        self._oversight_project_id = pid
        self._browser = browser
        self._smaker = smaker

    def sponsorships(self, uid):
        decision, candidate, dc = _sponsor_queries(self._oversight_project_id,
                                                   len(self.institutions))

        # mysql work-around for
        # 1248, 'Every derived table must have its own alias'
        dc = dc.alias('mw')
        q = dc.select(and_(dc.c.candidate == uid,
                           dc.c.decision == DecisionRecords.YES))

        return self._smaker().execute(q).fetchall()

    def oversight_decisions(self):
        '''In order to facilitate email notification of committee
        decisions, find decisions where notification has not been sent.
        '''
        cd, who, cdwho = _sponsor_queries(self._oversight_project_id,
                                          len(self.institutions))

        # decisions without notifications
        nl = notice_log
        dwn = cd.outerjoin(nl).select() \
            .with_only_columns(cd.columns).where(nl.c.record == None)
        return self._smaker().execute(dwn).fetchall()

    def decision_detail(self, record):
        avl = list(redcapdb.allfields(self._smaker(),
                                      self._oversight_project_id,
                                      record))
        browser = self._browser
        team = [browser.lookup(user_id)
                for user_id in
                [v for a, v in avl if v and a.startswith('user_id_')]]

        d = dict(avl)
        investigator = browser.lookup(d['user_id'])
        return investigator, team, d


class _DataDict(object):
    '''
    .. todo:: use pkg_resources rather than os to get redcap_dd
    '''
    def __init__(self, name,
                 respath='../redcap_dd/', suffix='.csv'):
        import pkg_resources

        def open_it():
            return pkg_resources.resource_stream(
                __name__, respath + name + suffix)
        self._open = open_it

    def fields(self):
        import csv
        rows = csv.DictReader(self._open())
        for row in rows:
            yield row["Variable / Field Name"], row

    def radio(self, field_name):
        for n, row in self.fields():
            if n == field_name:
                choicetxt = row["Choices, Calculations, OR Slider Labels"]
                break
        else:
            raise KeyError
        return [tuple(choice.strip().split(", ", 1))
                for choice in choicetxt.split('|')]


def _sponsor_queries(oversight_project_id, parties):
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
      SELECT cd_record AS record, cd_decision AS decision, who_userid
      AS candidate, expire_dt_exp AS dt_exp
      FROM
        (SELECT
         cdwho.cd_record AS cd_record, cdwho.cd_decision AS cd_decision,
         cdwho.cd_count_1 AS cd_count_1, cdwho.who_record AS who_record,
         cdwho.who_userid AS who_userid, cdwho.expire_record AS
         expire_record, cdwho.expire_dt_exp AS expire_dt_exp
         FROM
           (SELECT
            cd.record AS cd_record, cd.decision AS cd_decision,
            cd.count_1 AS cd_count_1, who.record AS who_record,
            who.userid AS who_userid, expire.record AS expire_record,
            expire.dt_exp AS expire_dt_exp
            FROM
              (SELECT p.record AS record, p.value AS decision,
               count(*) AS count_1
               FROM
                 (SELECT redcap_data.record AS record,
                  redcap_data.field_name AS field_name,
                  redcap_data.value AS value
                  FROM redcap_data
                  WHERE redcap_data.project_id = :project_id_1) AS p
               WHERE p.field_name LIKE :field_name_1
               GROUP BY p.record, p.value HAVING count(*) = :count_2) AS cd
               JOIN
                 (SELECT p.record AS record, p.value AS userid
                  FROM
                    (SELECT redcap_data.record AS record,
                     redcap_data.field_name AS field_name,
                     redcap_data.value AS value
                     FROM redcap_data
                     WHERE redcap_data.project_id = :project_id_1) AS p
                  WHERE p.field_name LIKE :field_name_2) AS who
               ON who.record = cd.record
               LEFT OUTER JOIN
                 (SELECT p.record AS record, p.value AS dt_exp
                  FROM
                    (SELECT redcap_data.record AS record,
                     redcap_data.field_name AS field_name,
                     redcap_data.value AS value
                     FROM redcap_data
                     WHERE redcap_data.project_id = :project_id_1) AS p
                  WHERE p.field_name = :field_name_3) AS expire
               ON expire.record = cd.record) AS cdwho)

      >>> pprint(cdwho.compile().params)
      {u'count_2': 3,
       u'field_name_1': 'approve_%',
       u'field_name_2': 'user_id_%',
       u'field_name_3': 'date_of_expiration',
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
        proj.c.field_name.like('user_id_%')).alias('who')

    dt_exp = select((proj.c.record,
                     proj.c.value.label('dt_exp'))).where(
        proj.c.field_name == 'date_of_expiration').alias('expire')

    j = decision.join(candidate,
                      candidate.c.record == decision.c.record).\
                          outerjoin(dt_exp,
                                    dt_exp.c.record == decision.c.record).\
                                        alias('cdwho').select()

    cdwho = j.with_only_columns((j.c.cd_record.label('record'),
                                 j.c.cd_decision.label('decision'),
                                 j.c.who_userid.label('candidate'),
                                 j.c.expire_dt_exp.label('dt_exp')))

    return decision, candidate, cdwho


class Mock(injector.Module, rtconfig.MockMixin):
    @provides(KProjectId)
    def project_id(self):
        import redcap_connect
        return redcap_connect._test_settings.project_id

    @classmethod
    def mods(cls):
        import medcenter
        return redcapdb.Mock.mods() + medcenter.Mock.mods() + [cls()]


class RunTime(rtconfig.IniModule):  # pragma nocover
    @provides(KProjectId)
    def project_id(self):
        rt = self.get_options(['project_id'], OVERSIGHT_CONFIG_SECTION)
        return rt.project_id

    @classmethod
    def mods(cls, ini):
        return [im
                for m in (redcapdb, medcenter)
                for im in m.RunTime.mods(ini)] + [cls(ini)]


def _integration_test():  # pragma nocover
    (ds, ) = RunTime.make(None, [DecisionRecords])

    print "pending notifications:", ds.oversight_decisions()


if __name__ == '__main__':  # pragma nocover
    _integration_test()
