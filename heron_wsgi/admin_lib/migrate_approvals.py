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

    >>> from heron_policy import _redcap_open, _redcap_fields
    >>> ddict = list(_redcap_fields(_redcap_open('system_access')))
    >>> Migration.saa_schema[1:] == tuple([n for n, etc in ddict][1:])
    True

    >>> from heron_policy import _redcap_radio
    >>> choices = dict(_redcap_radio('agree', _redcap_open('system_access')))
    >>> choices[Migration.YES] == 'Yes'
    True

    >>> from heron_policy import _redcap_open, _redcap_fields
    >>> fs = set([n for n, etc in _redcap_fields(_redcap_open('oversight'))])
    >>> set(['user_id_1', 'user_id_10']) - fs
    set([])
    '''
    YES = '1'
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
        log.debug('signatures: %s', sigs[:limit])

        self._saaproxy.post_csv(records=[self.saa_schema] +
                                [(sig[0], sig[1], sig[2], self.YES)
                                 for sig in sigs[:limit]],
                                type='flat')

    def migrate_droc(self, limit=5):
        s = self._smaker()
        oversight_request = self._table(s, 'oversight_request')
        sponsorship_candidates = self._table(s, 'sponsorship_candidates')

        reqs = s.execute(oversight_request.select()).fetchmany(limit)  #@@
        candidates = dict(((k, list(igroup)) for k, igroup in
                           groupby(s.execute(sponsorship_candidates.select()
                                             ).fetchall(),
                                   itemgetter(0))))

        records = [dict(skipnulls(req) + user_fields(
                    candidates.get(req['request_id'], [])))
                   for req in reqs]

        log.debug('droc requests: %s', pformat(records[:limit]))

        # todo: post records to API
        raise NotImplementedError


def skipnulls(row):
    return [(k, v) for k,v in row.items()
            if v is not None]

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

