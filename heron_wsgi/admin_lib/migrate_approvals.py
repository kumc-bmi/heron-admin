'''migrate_approvals -- migrate approval records from Oracle to REDCap/mysql
'''

import sys
import logging
import urllib

from injector import inject
from sqlalchemy.orm.session import Session

import i2b2pm
import config
from heron_policy import RunTime, SAA_CONFIG_SECTION, OVERSIGHT_CONFIG_SECTION
import redcap_connect

log = logging.getLogger(__name__)


def main():
    logging.basicConfig(level=logging.DEBUG, stream=sys.stderr)
    depgraph = RunTime.depgraph()
    mi = depgraph.get(Migration)
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

    def migrate_saa(self, limit=5):
        s = self._smaker()
        sigs = s.execute('select rownum, user_id, user_full_name, '
                         " to_char(signed_date, 'yyyy-mm-dd hh:mm:ss') when"
                         ' from heron.system_access_users').fetchall()
        log.debug('signatures: %s', sigs[:limit])

        self._saaproxy.post_csv(records=[self.saa_schema] +
                                [(sig[0], sig[1], sig[2], self.YES)
                                 for sig in sigs[:limit]],
                                type='flat')


    def oracle_saa_users(self):
        s = self._smaker()
        ans = s.execute('select * from heron.system_access_users')
        return ans.fetchall()


if __name__ == '__main__':
    main()

