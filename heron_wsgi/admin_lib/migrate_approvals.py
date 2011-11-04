'''migrate_approvals -- migrate approval records from Oracle to REDCap/mysql
'''

import sys
import logging
import urllib
from itertools import groupby, izip
from operator import itemgetter
from pprint import pformat

from injector import inject
from sqlalchemy.orm.session import Session
from sqlalchemy import Table, Column, select, text
from sqlalchemy.types import Integer, String
from sqlalchemy.sql import func

import i2b2pm
import config
from heron_policy import RunTime, SAA_CONFIG_SECTION, OVERSIGHT_CONFIG_SECTION
import redcap_connect
from orm_base import Base

log = logging.getLogger(__name__)


def main():
    logging.basicConfig(level=logging.DEBUG, stream=sys.stderr)
    depgraph = RunTime.depgraph()
    mi = depgraph.get(Migration)
    mi.migrate_droc()
    mi.migrate_saa()


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
    NO = '0'
    saa_schema = ('participant_id', 'user_id', 'full_name', 'agree')

    @inject(smaker=(Session, i2b2pm.CONFIG_SECTION),
            rt_saa=(config.Options, SAA_CONFIG_SECTION),
            rt_droc=(config.Options, OVERSIGHT_CONFIG_SECTION),
            ua=urllib.URLopener)
    def __init__(self, smaker, ua, rt_saa, rt_droc):
        self._smaker = smaker
        self._saaproxy = redcap_connect.endPoint(ua, rt_saa.api_url,
                                                 rt_saa.token)
        self._drocproxy = redcap_connect.endPoint(ua, rt_droc.api_url,
                                                  rt_droc.token)

    def _table(self, session, name):
        return Table(name, Base.metadata, schema='heron',
                     autoload=True, autoload_with=session.bind)

    def migrate_saa(self, limit=5):
        s = self._smaker()
        system_access_users = self._table(s, 'system_access_users')

        sigs = s.execute(select((text('rownum'),
                                 system_access_users))).fetchall()

        log.debug('signature fields: %s', pformat(sigs[0].items()))
        records = [dict(participant_id=sig['rownum'],
                        user_id=sig['user_id'],
                        full_name=sig['user_full_name'],
                        agree=self.YES)
                   for sig in sigs[:limit]]

        log.debug('signature records: %s', pformat(records))
        self._saaproxy.post_json(content='record',
                                 data=records,
                type='flat')

    def migrate_droc(self, limit=5):
        s = self._smaker()
        oversight_request = self._table(s, 'oversight_request')
        sponsorship_candidates = self._table(s, 'sponsorship_candidates')

        reqs = s.execute(oversight_request.select()).fetchall()
        candidates = dict(((k, list(igroup)) for k, igroup in
                           groupby(s.execute(sponsorship_candidates.select()
                                             ).fetchall(),
                                   itemgetter(0))))

        records = [dict(rowitems(req, 'request_id')
                        + [('participant_id', int(req['request_id']))]
                        + user_fields(candidates.get(req['request_id'], [])))
                   for req in reqs]

        log.debug('droc requests: %s', pformat(records[:limit]))

        log.debug('droc record ids: %s',
                  [rec['participant_id'] for rec in records])

        self._drocproxy.post_json(content='record', data=records[:limit])  #@@


def rowitems(row, k_skip):
    return [(k, v)
            for k,v in row.items()
            if v is not None and k != k_skip]

def user_fields(cg):
    '''
    >>> user_fields([{'user_id': 'jd', 'kumc_employee': '1',
    ...               'affiliation': ''},
    ...              {'user_id': 'xyz', 'kumc_employee': '2',
    ...               'affiliation': 'explain'}])
    ... # doctest: +NORMALIZE_WHITESPACE
    [('user_id_1', 'jd'), ('kumc_employee_1', '1'), ('affiliation_1', ''),
     ('user_id_2', 'xyz'), ('kumc_employee_2', '2'),
         ('affiliation_2', 'explain')]
    '''
    log.debug('candidate group: %s', pformat(cg))
    f = []
    for ix, candidate in zip(range(len(cg)), cg):
        f.extend([('%s_%s' % (field_name, ix + 1), candidate[field_name])
                  for field_name
                  in ('user_id', 'kumc_employee', 'affiliation')
                  if candidate[field_name] is not None])
    log.debug('candidate group fields: %s', pformat(f))
    return f



if __name__ == '__main__':
    main()

