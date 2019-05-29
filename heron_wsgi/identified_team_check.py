"""identified_team_check -- check for IRB OK on identified teams
"""

from pprint import pformat
import logging

from sqlalchemy import and_, select

from admin_lib import redcapdb
from admin_lib.ldaplib import CONFIG_SECTION as ENTERPRISE_DIRECTORY_CONFIG
from admin_lib.medcenter import ECompliance
from admin_lib.ocap_file import Path
from admin_lib.rtconfig import RuntimeOptions

log = logging.getLogger(__name__)


def integration_test(argv, cwd, build_opener,
                     create_engine):
    [record, pid] = argv[1:3]
    log.info('checking study team for record %s in project %s', record, pid)

    ini = cwd / 'integration-test.ini'

    def ecompliance_svc():
        edir = RuntimeOptions(ini, ['studylookupaddr'],
                              ENTERPRISE_DIRECTORY_CONFIG)

        log.debug('studyTeam at: %s', edir.studylookupaddr)
        return ECompliance.make(edir.studylookupaddr, build_opener())

    def heron_oversight_db():
        redcap_config = RuntimeOptions(ini, ['engine'],
                                       redcapdb.CONFIG_SECTION)
        return create_engine(redcap_config.engine)

    req = OversightRequest(heron_oversight_db(), record, pid)
    log.debug('request info...')
    project = req.get_info()
    log.info('request info: %s', dict(project.items()))

    log.debug('getting team for %s:', project.hsc_number)
    ec = ecompliance_svc()
    current = ec.lookup(project.hsc_number)
    log.info('current team for %s: %s', project.hsc_number,
             [member['lastName'] +
              ('*' if member['accountDisabled'] else '')
              for member in current])
    approved = [who for who in current
                if not who['accountDisabled']]

    req_team, ok, bad = req.check_team(approved)
    log.info('requested team:\n%s',
             pformat([dict(row.items()) for row in req_team]))
    log.info('requested team ok: %s', [row.team_email for row in ok])
    log.info('requested team bad: %s', [row.team_email for row in bad])


class OversightRequest(object):
    def __init__(self, db, record, pid):
        self.__db = db
        self.pid = pid
        self.record = record

    def _constrain(self, where, cols):
        return and_(where,
                    cols[0] == self.pid,
                    cols[1] == self.record)

    def get_info(self):
        cols, from_obj, where, _rel = redcapdb.unpivot(
            ['hsc_number', 'project_title'], record=True)
        find_project = select(
            cols, self._constrain(where, cols), from_obj=from_obj)
        log.debug('find_project:\n\n%s\n\n', find_project)
        return self.__db.execute(find_project).first()

    def check_team(self, approved,
                   max_members=10):
        requested, ok, bad = [], [], []
        user_cols = ['user_id', 'team_email', 'name_etc']

        for ix in range(1, max_members + 1):
            cols, from_obj, where, _rel = redcapdb.unpivot(
                ['%s_%s' % (field, ix) for field in user_cols],
                record=True)
            find_mem = select(
                # strip _N off column names
                cols[:2] + [col.label(name)
                            for col, name in zip(cols[2:], user_cols)],
                self._constrain(where, cols), from_obj=from_obj)
            log.debug('find_mem: %s', find_mem)
            mem = self.__db.execute(find_mem).first()
            if not mem or not mem.user_id:
                break

            requested.append(mem)
            for who in approved:
                # log.debug(pformat([dict(mem.items()),
                #                    '%s =?= %s',
                #                    who]))
                if mem.team_email == who['EmailPreferred']:
                    ok.append(mem)
                    break
            else:
                bad.append(mem)

        return requested, ok, bad


if __name__ == '__main__':
    def _script():
        from io import open as io_open
        from os.path import join as joinpath, exists
        from sys import argv
        from urllib2 import build_opener

        from sqlalchemy import create_engine

        cwd = Path('.', open=io_open, joinpath=joinpath, exists=exists)

        logging.basicConfig(
            level=logging.DEBUG if '--debug' in argv
            else logging.INFO)

        integration_test(argv[:], cwd, build_opener,
                         create_engine)

    _script()
