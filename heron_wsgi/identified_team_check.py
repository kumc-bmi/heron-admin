"""identified_team_check -- check for IRB OK on identified teams

Suppose we have a HERON oversight request regarding a cure for warts::

    >.. logging.basicConfig(level=logging.DEBUG)
    >>> io = MockIO()
    >>> db = redcapdb.Mock.engine()
    >>> record_id = '6373469799195807417'
    >>> oreq = OversightRequest(db, record_id, io.oversight_project)
    >>> research = oreq.get_info()
    >>> research
    (34, u'6373469799195807417', u'HSC123', u'Cure Warts')

The request is to give several team members access to data:

    >>> [item.user_id for item in oreq.requested()]
    [u'some.one', u'carol.student', u'koam.rin']

But not all of them are in the HSC records for this study:

    >>> approved = io.datasrc.lookup(research.hsc_number)
    >>> [detail['EmailPreferred'] for detail in approved]
    ['some.one@example']

When we try to pair up the requested team members with the approved
team members, we note there are some left over:

    >>> compliant = oreq.check_team(approved)
    >>> [wanted['user_id'] for wanted, ok in compliant if not ok]
    [u'carol.student', u'koam.rin']

All this is packaged up as a web page view:

    >>> from paste.fixture import TestApp
    >>> with Configurator() as config:
    ...     rt1 = OversightRequest.configure_view(
    ...         config, db, io.oversight_project, io.datasrc)
    ...     config.add_route(rt1, '/')
    ...     tapp = TestApp(config.make_wsgi_app())

    >>> r1 = tapp.get('/?record_id=%s' % record_id)
    >>> print(r1.body)  # doctest: +ELLIPSIS +NORMALIZE_WHITESPACE
    {
      "study": { ...
        "Full Study Title": "Cure Warts"
      },
      "team": [ ...
          {
            "team_email": "some.one@example", ...
          },
          {
            "EmailPreferred": "some.one@example", ...
          }
        ],
        [
          {
            "team_email": "carol.student@example",
            "user_id": "carol.student", ...
          },
          null
        ], ...
      ]
    }

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
    def configure_view(cls, config, db, pid, datasrc,
                       route_name='check'):
        view = cls.make_view(db, pid, datasrc)
        config.add_view(view, route_name=route_name)
        return route_name

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
            if not current:
                raise HTTPBadRequest(
                    detail='No team found for %s' % project.hsc_number)
            study = {k: current[0][k]
                     for k in ['State', 'Date Expiration', 'Full Study Title']}
            compliant = hreq.check_team(current)
            return Response(json.dumps(
                dict(study=study, team=compliant), indent=2))

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
        log.debug('find_project %s in %s:\n\n%s\n\n',
                  self.record, self.pid, find_project)
        it = self.__db.execute(find_project).first()
        if it is None:
            raise IOError(self.record)
        return it

    def check_team(self, current):
        approved = [who for who in current
                    if not who.get('accountDisabled')]

        # rows aren't JSON serializable
        row2dict = lambda row: dict(row.items())  # noqa

        def check1(mem):
            for who in approved:
                # log.debug(pformat([dict(mem.items()),
                #                    '%s =?= %s',
                #                    who]))
                if mem.team_email == who['EmailPreferred']:
                    return row2dict(mem), who
            else:
                return row2dict(mem), None

        return [check1(m) for m in self.requested()]

    def requested(self,
                  max_members=10):

        rd = redcapdb.redcap_data
        record_data = select([rd]).where(and_(
            rd.c.project_id == self.pid,
            rd.c.record == self.record,
        )).alias('rec')

        def get1(ix):
            [uf, tf, nf] = [
                select([
                    record_data.c.value.label(field)
                ]).where(
                    record_data.c.field_name == '%s_%s' % (field, ix)
                ).alias('j_' + field)
                for field in ['user_id', 'team_email', 'name_etc']]
            find_mem = select(
                [uf.c.user_id, tf.c.team_email, nf.c.name_etc],
                from_obj=uf.join(tf, tf.c.team_email > '', isouter=True)
                .join(nf, nf.c.name_etc > '', isouter=True))
            log.debug('find_mem: %s', find_mem)
            return self.__db.execute(find_mem).first()

        requested = []
        for ix in range(1, max_members + 1):
            mem = get1(ix)
            if not mem:
                break
            requested.append(mem)

        return requested


class MockIO(object):
    oversight_project = 34
    record_id = '6373469799195807417'

    @property
    def datasrc(self):
        return self

    def lookup(self, hsc_number):
        return [{
            'EmailPreferred': 'some.one@example',
            'State': 'OK',
            'Date Expiration': '2030-01-01',
            'Full Study Title': 'Cure Warts',
        }]


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
            r1 = OversightRequest.configure_view(
                config, self.__redcap_db, self.project_id, self.__datasrc)
            config.add_route(r1, '/')
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
                  ('*' if member.get('accountDisabled') else '')
                  for member in current])

        team = req.check_team(current)
        log.info('team as requested, paired with any HSC approved detail:\n%s',
                 pformat(team))


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
