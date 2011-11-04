'''migrate_approvals -- migrate approval records from Oracle to REDCap/mysql
'''

import sys
import logging
import urllib

from injector import inject
from sqlalchemy.orm.session import Session

import i2b2pm
import config
from heron_policy import RunTime, OVERSIGHT_CONFIG_SECTION
import redcap_connect

log = logging.getLogger(__name__)


def main():
    logging.basicConfig(level=logging.DEBUG, stream=sys.stderr)
    depgraph = RunTime.depgraph()
    mi = depgraph.get(Migration)
    mi.migrate_saa()


class Migration(object):
    @inject(smaker=(Session, i2b2pm.CONFIG_SECTION),
            opts=(config.Options, OVERSIGHT_CONFIG_SECTION),
            ua=urllib.URLopener)
    def __init__(self, smaker, opts, ua):
        self._smaker = smaker
        self._proxy = redcap_connect.endPoint(ua, opts.api_url, opts.token)

    def migrate_saa(self):
        s = self._smaker()
        sigs = s.execute('select user_id, user_full_name, '
                         " to_char(signed_date, 'yyyy-mm-dd hh:mm:ss') when"
                         ' from heron.system_access_users').fetchall()
        log.debug('signatures: %s', sigs[:5])

    def oracle_saa_users(self):
        s = self._smaker()
        ans = s.execute('select * from heron.system_access_users')
        return ans.fetchall()


if __name__ == '__main__':
    main()

