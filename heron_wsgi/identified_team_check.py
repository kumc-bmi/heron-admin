"""identified_team_check -- check for IRB OK on identified teams
"""

from pprint import pformat
import json
import logging

from pyramid.config import Configurator
from pyramid.httpexceptions import HTTPBadRequest
from pyramid.response import Response
from sqlalchemy import and_, select

from admin_lib import heron_policy
from admin_lib import ldaplib
from admin_lib import redcapdb
from admin_lib.medcenter import HSCRecords
from admin_lib.ocap_file import Path
from admin_lib.rtconfig import RuntimeOptions

log = logging.getLogger(__name__)


class OversightRequest(object):
    def __init__(self, db, record, pid):
        self.__db = db
        self.pid = pid
        self.record = record

    @classmethod
    def _bootstrap(cls, ini, create_engine):
        redcap_config = RuntimeOptions(
            ini, ['engine'], redcapdb.CONFIG_SECTION)
        db = create_engine(redcap_config.engine)
        oversight_config = RuntimeOptions(
            ini, ['project_id'], heron_policy.OVERSIGHT_CONFIG_SECTION)
        return db, oversight_config.project_id

    @classmethod
    def make_view(cls, db, pid, datasrc):
        def view(request):
            try:
                record_id = request.GET.getone('record_id')
            except KeyError:
                raise HTTPBadRequest(detail='Missing record_id')
            hreq = cls(db, record_id, pid)
            project = hreq.get_info()
            log.info('HERON oversight request %s: %s',
                     record_id, dict(project.items()))
            current = datasrc.lookup(project.hsc_number)
            req_team, ok, bad = hreq.check_team(current)
            r2d = lambda r: dict(r.items())  # noqa
            return Response(json.dumps(dict(
                requested=map(r2d, req_team),
                ok=map(r2d, ok),
                bad=map(r2d, bad),
            ), indent=2))

        return view

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

    def check_team(self, current,
                   max_members=10):
        #@@ISSUE: study["State"], study["Date Expiration"]
        approved = [who for who in current
                    if not who['accountDisabled']]
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


class IntegrationTest(object):
    def __init__(self, datasrc, redcap_db, pid):
        self.__datasrc = datasrc
        self.__redcap_db = redcap_db
        self.project_id = pid

    @classmethod
    def make(cls, cwd, urlopener, create_engine,
             config_fn='integration-test.ini'):
        ini = cwd / config_fn
        db, pid = OversightRequest._bootstrap(ini, create_engine)
        edir = RuntimeOptions(ini, ['studylookupaddr'], ldaplib.CONFIG_SECTION)
        log.debug('studyTeam at: %s', edir.studylookupaddr)
        datasrc = HSCRecords(edir.studylookupaddr, urlopener)
        return cls(datasrc, db, pid)

    def run_server(self, make_server,
                   host='localhost',
                   port=6543):
        with Configurator() as config:
            view = OversightRequest.make_view(
                self.__redcap_db, self.project_id, self.__datasrc)
            config.add_route('check', '/')
            config.add_view(view, route_name='check')
            app = config.make_wsgi_app()
        server = make_server(host, port, app)
        server.serve_forever()

    def main(self, argv):
        [record] = argv[1:2]

        log.info('checking study team for record %s in project %s',
                 record, self.project_id)

        req = OversightRequest(self.__redcap_db, record, self.project_id)
        log.debug('request info...')
        project = req.get_info()
        log.info('request info: %s', dict(project.items()))

        log.debug('getting team for %s:', project.hsc_number)

        current = self.__datasrc.lookup(project.hsc_number)
        # ISSUE: I don't see the P.I. on the HERON team.
        log.info('current team for %s: %s', project.hsc_number,
                 [member['lastName'] +
                  ('*' if member['accountDisabled'] else '')
                  for member in current])

        req_team, ok, bad = req.check_team(current)
        log.info('requested team:\n%s',
                 pformat([dict(row.items()) for row in req_team]))
        log.info('requested team ok: %s', [row.team_email for row in ok])
        log.info('requested team bad: %s', [row.team_email for row in bad])


if __name__ == '__main__':
    def _script():
        from io import open as io_open
        from os.path import join as joinpath, exists
        from sys import argv
        from urllib2 import build_opener
        from wsgiref.simple_server import make_server

        from sqlalchemy import create_engine

        cwd = Path('.', open=io_open, joinpath=joinpath, exists=exists)

        logging.basicConfig(
            level=logging.DEBUG if '--debug' in argv
            else logging.INFO)

        test = IntegrationTest.make(cwd, build_opener(), create_engine)
        if '--serve' in argv:
            test.run_server(make_server)
        else:
            test.main(argv[:])

    _script()
