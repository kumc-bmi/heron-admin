'''migrate_approvals -- migrate approval records from Oracle to REDCap/mysql


insert into redcap.redcap_surveys_response (
participant_id,
record,
first_submit_time,
completion_time)
select p.participant_id, d.record, current_timestamp, current_timestamp
from redcap.redcap_surveys_participants AS p
join (
select distinct r1.record, concat(r2.value, '@kumc.edu') as email
from redcap.redcap_data r1
join redcap.redcap_data r2 on r1.project_id=r2.project_id
  and r1.record=r2.record
where r1.project_id=237
and r2.field_name='user_id'
and r2.record not in ('jdenton', 'achoudhary', 'mmishra-aff',
  'jburns2', 'rwaitman')
) d
on p.participant_email = d.email
;

'''
import logging
import sys
import urllib
from itertools import groupby
from operator import itemgetter
from pprint import pformat

from injector import inject
from sqlalchemy import Table, select, text
from sqlalchemy.orm.session import Session

import rtconfig
import heron_policy
import i2b2pm
import medcenter
import noticelog
import redcap_connect
import redcapdb
from heron_policy import RunTime, SAA_CONFIG_SECTION, OVERSIGHT_CONFIG_SECTION
from i2b2pm import Base
from disclaimer import AcknowledgementsProject


log = logging.getLogger(__name__)


def main():
    logging.basicConfig(level=logging.DEBUG, stream=sys.stderr)
    mi, md = RunTime.make(None, [Migration, MigrateDisclaimers])

    if '--disclaimers' in sys.argv:
        md.migrate_acks()
    elif '--since' in sys.argv:
        when = sys.argv[-1]
        mi.migrate_droc(since=when)
    else:
        print "System access agreements: ", mi.migrate_saa()
        print "DROC requests:", mi.migrate_droc()


class Migration(object):
    '''

    At test time, check constants here against the data dictionary:

    >>> from heron_policy import _DataDict
    >>> ddict = _DataDict('system_access')
    >>> Migration.saa_schema[1:] == tuple([n for n, etc in ddict.fields()][1:])
    True

    >>> choices = dict(ddict.radio('agree'))
    >>> choices[Migration.YES] == 'Yes'
    True

    >>> droc_ddict = _DataDict('oversight')
    >>> fs = set([n for n, etc in droc_ddict.fields()])
    >>> set(['user_id_1', 'user_id_10']) - fs
    set([])

    >>> [desc['Field Type'] for n, desc in droc_ddict.fields()
    ...  if n == 'kumc_employee_5']
    ['yesno']
    '''
    YES = '1'
    COMPLETE = '2'
    NO = '0'
    saa_schema = ('participant_id', 'user_id', 'full_name', 'agree')

    @inject(olddb=(Session, i2b2pm.CONFIG_SECTION),
            newdb=(Session, redcapdb.CONFIG_SECTION),
            rt_saa=(rtconfig.Options, SAA_CONFIG_SECTION),
            rt_droc=(rtconfig.Options, OVERSIGHT_CONFIG_SECTION),
            mc=medcenter.MedCenter,
            hp=heron_policy.HeronRecords,
            ua=urllib.URLopener)
    def __init__(self, olddb, newdb, ua, rt_saa, rt_droc, mc, hp):
        self._smaker = olddb
        self._newdb = newdb
        self._saaproxy = redcap_connect.endPoint(ua, rt_saa.api_url,
                                                 rt_saa.token)
        self._drocproxy = redcap_connect.endPoint(ua, rt_droc.api_url,
                                                  rt_droc.token)
        self._mc = mc
        self._hp = hp

    def migrate_saa(self):
        s = self._smaker()
        system_access_users = _table(s, 'system_access_users')

        sigs = s.execute(select((text('rownum'),
                                 system_access_users))).fetchall()

        log.debug('signature fields: %s', pformat(sigs[0].items()))
        log.info('signatures: %s', pformat([sig['user_id'] for sig in sigs]))

        lookup = self._mc.lookup
        hp = self._hp

        for sig in sigs:
            badge = lookup(sig['user_id'].strip())
            closure_kludge = [None]

            def save(ans):
                closure_kludge[0] = ans
            hp._saa_rc(badge.cn,
                       dict(user_id=badge.cn, full_name=badge.sort_name()),
                       ans_kludge=save)
            log.debug('survey setup ans: %s', closure_kludge[0])

        records = [dict(participant_id=sig['rownum'],
                        user_id=sig['user_id'].strip(),
                        full_name=lookup(sig['user_id'].strip()).full_name(),
                        agree=self.YES,
                        agreement_complete=self.COMPLETE)
                   for sig in sigs]

        log.debug('signature records: %s', pformat(records))
        n = self._saaproxy.record_import(data=records,
                                         overwriteBehavior='overwrite')

        return len(sigs), n

    def migrate_droc(self, since=None):
        s = self._smaker()
        oversight_request = _table(s, 'oversight_request')
        sponsorship_candidates = _table(s, 'sponsorship_candidates')

        if since:
            oversight_request = oversight_request.select().where(
                oversight_request.c.request_id > since).alias('since')

        reqs = s.execute(oversight_request.select()).fetchall()
        candidates = dict(((k, list(igroup)) for k, igroup in
                           groupby(s.execute(sponsorship_candidates.select()).\
                                       fetchall(),
                                   itemgetter(0))))

        log.info('Oversight Requests: %s',
                 pformat([(req['request_id'],
                           req['user_id'],
                           req['project_title'])
                          for req in reqs]))
        lookup = self._mc.lookup
        records = [dict(rowitems(req,
                                 ('request_id', 'approval_time', 'full_name'))
                        + [('full_name', lookup(req['user_id'].strip()).\
                                full_name())]
                        + [('participant_id', int(req['request_id']))]
                        + [('heron_oversight_request_complete', self.COMPLETE)]
                        + user_fields(lookup,
                                      candidates.get(req['request_id'], [])))
                   for req in reqs]

        log.debug('droc requests: %s', pformat(records[:5]))

        n = self._drocproxy.record_import(data=records)
        log_notices(self._newdb(), reqs)

        return len(reqs), n


def _table(session, name, schema='heron'):
    return Table(name, Base.metadata, schema=schema,
                 autoload=True, autoload_with=session.bind)


def log_notices(s, reqs):
    s.execute(noticelog.notice_log.insert(),
              [dict(record=int(req['request_id']),
                    timestamp=req['approval_time'])
               for req in reqs])
    s.commit()


def rowitems(row, k_skips):
    return [(k, v)
            for k, v in row.items()
            if v is not None and k not in k_skips]


def user_fields(lookup, cg):
    r'''
    >>> user_fields(_test_lookup,
    ...             [{'user_id': 'John.Doe', 'kumc_employee': '1',
    ...               'affiliation': ''},
    ...              {'user_id': 'Alice.Jones', 'kumc_employee': '2',
    ...               'affiliation': 'explain'}])
    ... # doctest: +NORMALIZE_WHITESPACE
    [('user_id_1', 'John.Doe'), ('kumc_employee_1', '1'),
    ('affiliation_1', ''), ('name_etc_1',
    'Doe, John\nSanitation Engineer\nMail Department'),
    ('user_id_2', 'Alice.Jones'),
    ('kumc_employee_2', '2'), ('affiliation_2', 'explain'),
    ('name_etc_2', 'Jones, Alice\nSanitation Engineer\nMail Department')]

    '''
    log.debug('candidate group: %s', pformat(cg))
    f = []
    for ix, candidate in zip(range(len(cg)), cg):
        f.extend([('%s_%s' % (field_name, ix + 1),
                   candidate[field_name].strip())
                  for field_name
                  in ('user_id', 'kumc_employee', 'affiliation')
                  if candidate[field_name] is not None])

        a = lookup(candidate['user_id'].strip())
        f.append(('name_etc_%d' % (ix + 1),
                  '%s, %s\n%s\n%s' % (
                    a.sn, a.givenname, a.title, a.ou)))

    log.debug('candidate group fields: %s', pformat(f))
    return f


def _test_lookup(uid):
    return medcenter.Badge(cn=uid,
                           sn=uid.split('.')[1],
                           givenname=uid.split('.')[0],
                           mail='%s@example' % uid,
                           ou='Mail Department',
                           title='Sanitation Engineer')


class MigrateDisclaimers(object):
    @inject(olddb=(Session, i2b2pm.CONFIG_SECTION),
            acksproj=AcknowledgementsProject)
    def __init__(self, olddb, acksproj):
        self._i2b2db = olddb
        self._ap = acksproj

    def migrate_acks(self):
        si = self._i2b2db()
        old_disc = _table(si, 'disclaimers')
        old_acks = _table(si, 'acknowledged_disclaimers')

        ans = si.execute(old_disc.select().where(old_disc.c.is_recent == 1))
        recent_disc = ans.fetchone()
        log.info('current disclaimer: %s',
                 recent_disc['disclaimer_url'])

        acks = si.execute(old_acks.select().where(
                old_acks.c.disclaimer_id == recent_disc['disclaimer_id']))

        whowhen = [(ack['user_id'], ack['acknowledge_tmst']) for ack in acks]
        log.info('acked users: %s', whowhen)
        self._ap.add_records(recent_disc['disclaimer_url'], whowhen)


if __name__ == '__main__':
    main()
