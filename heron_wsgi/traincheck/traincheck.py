r'''traincheck -- check human subjects training records via CITI

Usage:
  traincheck refresh --user=NAME [--wsdl=U --pwenv=K --dbadmin=K -d]
  traincheck backfill --full=F1 --refresher=F1 --in-person=F3 [--dbadmin=K -d]
  traincheck combine --exempt=PID [--dbadmin=K -d]
  traincheck lookup NAME [--dbrd=K -d]
  traincheck --help

Options:
  NAME               userid of user whose training records are sought
  --dbrd=K           read access to PII DB: name of environment variable
                     with sqlalchemy URL
                     [default: HSR_TRAIN_CHECK]
  --dbadmin=K        admin (create, delete, ...) access to PII DB
                     [default: HSR_TRAIN_ADMIN]
  --exempt=PID       exempt records REDCap project ID
  --wsdl=URL         access to CITI SOAP Service: Service Description URL
                     [default: https://webservices.citiprogram.org/SOAP/CITISOAPService.asmx?WSDL]  # noqa
  --user=NAME        access to CITI SOAP Service: username
  --pwenv=K          access to CITI SOAP Service: password environment variable
                     [default: CITI_PASSWORD]
  -d --debug         turn on debug logging
  backfill           Load data from legacy system
  combine            create view combining training data from all sources

PII DB is a database suitable for PII (personally identifiable information).

.. note:: This directive separates usage doc above from design notes below.


Make Local Copy of CITI Data
----------------------------

Our human subjects training is provided by the Collaborative
Institutional Training Initiative (CITI__). In order to facilitate
verifying that a HERON user's human subjects training is current, we
regularly refresh a copy of the CITI Data via their Web Service, using
authorization from the command line and environment as noted above::

    >>> s1 = Mock()  # scenario 1
    >>> stdout = s1.stdout
    >>> main(stdout, s1.cli_access('traincheck refresh --user=MySchool'))

__ https://www.citiprogram.org/

The course completion reports are now stored in the database::

    >>> for exp, name, course in s1._db.execute("""
    ...     select dteExpiration, InstitutionUserName, strCompletionReport
    ...     from CRS limit 3"""):
    ...     print exp[:10], name, course
    2000-12-22 ssttt sss
    2000-01-13 sss Basic/Refresher Course - Human Subjects Research
    2000-02-04 sssstttt Basic/Refresher Course - Human Subjects Research


Backfill
--------

We get data from the legacy system in CSV format:

    >>> with s1.openf('f.csv') as datafile:
    ...     print datafile.read()
    FirstName,LastName,Email,EmployeeID,DateCompleted,Username
    R,S,RS@example,J1,8/4/2011 0:00,rs

Using access to this data and the database, we load it::

    >>> main(stdout, s1.cli_access(
    ...     'traincheck backfill '
    ...          '--full=f.csv --refresher=r.csv --in-person=i.csv',
    ...     db=s1._db))  # (Don't make a new in-memory DB)

The results are straightforward::

    >>> for passed, name in s1._db.execute(
    ...     'select CompleteDate, Username from HumanSubjectsRefresher'):
    ...     print passed[:10], name
    2013-08-04 rs3


Combine sources into a view
---------------------------

    >>> main(stdout, s1.cli_access('traincheck combine --exempt=123',
    ...      db=s1._db))  # (Don't make a new in-memory DB)

    >>> HSR('').combo_view
    'hsr_training_combo'

    >>> for who, expired, completed, course in s1._db.execute(
    ...     'select * from hsr_training_combo order by expired'):
    ...     print "%-8s %s %s" % (who, expired[:10], course)
    sss      2000-01-13 Basic/Refresher Course - Human Subjects Research
    sssstttt 2000-02-04 Basic/Refresher Course - Human Subjects Research
    sttttt   2000-04-12 Basic/Refresher Course - Human Subjects Research
    rs       2012-08-04 HumanSubjectsFull
    rs2      2013-08-04 HumanSubjectsInPerson
    rs3      2014-08-04 HumanSubjectsRefresher


Find Training Records
---------------------

While we support checking records from the CLI, it will typically be
done using the API. Given (read) access to the database, we can make
a `TrainingRecordsRd`::

    >>> rd = TrainingRecordsRd(acct=(conntrx(s1._db.connect()), None, None))

Now let's look up training for Sam, whose username is `sssstttt`::

    >>> rd['sssstttt'].expired
    u'2000-02-04 12:34:56.000000'

.. note:: TODO: Integrate a story-style name into test data.

But there's no training on file for Fred::

    >>> rd['fred']
    Traceback (most recent call last):
      ...
    KeyError: 'fred'


Course Naming
*************

The courses we're interested in are selected using::

    >>> ad = TrainingRecordsAdmin((lambda: s1._db.connect(), None, None), 0)
    >>> ad.course_pattern
    '%Human Subjects Research%'


'''

import logging
from xml.etree.ElementTree import fromstring as XML
from datetime import datetime

from sqlalchemy import (MetaData, Table, Column,
                        String, Integer, Date, DateTime,
                        select, union_all, literal_column, and_)
from sqlalchemy.engine.url import make_url

from lalib import maker, conntrx
from sqlaview import CreateView, DropView, year_after
import relation
import redcapview

VARCHAR120 = String(120)
log = logging.getLogger(__name__)


def main(stdout, access):
    cli = access()

    mkTRA = lambda: TrainingRecordsAdmin(cli.account('--dbadmin'), cli.exempt)

    if cli.refresh:
        svc = CitiSOAPService(cli.soapClient(), cli.auth)

        admin = mkTRA()
        for cls, k in [
                # smallest to largest typical payload
                (GRADEBOOK, svc.GetGradeBooksXML),
                (MEMBERS, svc.GetMembersXML),
                (CRS, svc.GetCompletionReportsXML)]:
            doc = svc.get(k)
            try:
                name, data = admin.docRecords(doc)
                admin.put(name, cls.parse_dates(data))
            except StopIteration:
                raise SystemExit('no records in %s' % k)
    elif cli.backfill:
        admin = mkTRA()
        for (opt, table_name, date_col) in Chalk.tables:
            data = cli.getRecords(opt)
            admin.put(table_name, Chalk.parse_dates(data, [date_col]))
    elif cli.combine:
        admin = mkTRA()
        admin.combine()
    else:
        store = TrainingRecordsRd(cli.account('--dbrd'))
        try:
            training = store[cli.NAME]
        except KeyError:
            raise SystemExit('no training records for %s' % cli.IDVAULT_NAME)
        log.info('training OK: %s', training)
        stdout.write(str(training))


class TableDesign(object):
    date_format = '%Y/%m/%d'
    maxlen = 100

    @classmethod
    def _parse(cls, txt):
        return (None if not txt else
                datetime.strptime(txt[:cls.maxlen], cls.date_format))

    @classmethod
    def parse_dates(cls, records, date_columns=None):
        if date_columns is None:
            date_columns = [c.name for c in cls.columns()
                            if isinstance(c.type, Date)
                            or isinstance(c.type, DateTime)]

        fix = lambda r: r._replace(**dict((col, cls._parse(getattr(r, col)))
                                          for col in date_columns))
        return [fix(r) for r in records]

    @classmethod
    def columns(cls):
        ty = lambda text: (
            Integer if text == '12345' else
            DateTime() if text == '2014-05-06T19:15:48' else
            Date() if text == '09/09/14' else
            VARCHAR120)

        return [Column(field.tag, ty(field.text))
                for field in XML(cls.markup)]

    @classmethod
    def xml_table(cls, meta, db_name):
        return Table(cls.__name__, meta,
                     *cls.columns(),
                     schema=db_name,
                     **redcapview.backend_options)


class CRS(TableDesign):
    '''
    >>> CRS._parse('2014-05-06T19:15:48.2-04:00')
    datetime.datetime(2014, 5, 6, 19, 15, 48)

    >>> CRS._parse('')
    >>> CRS._parse(None)

    '''

    date_format = '%Y-%m-%dT%H:%M:%S'

    # strip sub-second, timezone of data such as
    # 2014-05-06T19:15:48.2-04:00
    maxlen = len('2014-05-06T19:15:48')

    markup = '''
      <CRS>
        <CR_InstitutionID>12345</CR_InstitutionID>
        <MemberID>12345</MemberID>
        <EmplID />
        <StudentID>12345</StudentID>
        <InstitutionUserName>a</InstitutionUserName>
        <FirstName>a</FirstName>
        <LastName>a</LastName>
        <memberEmail>a</memberEmail>
        <AddedMember>2014-05-06T19:15:48</AddedMember>
        <strCompletionReport>a</strCompletionReport>
        <intGroupID>12345</intGroupID>
        <strGroup>a</strGroup>
        <intStageID>12345</intStageID>
        <intStageNumber>12345</intStageNumber>
        <strStage>a</strStage>
        <intCompletionReportID>12345</intCompletionReportID>
        <intMemberStageID>12345</intMemberStageID>
        <dtePassed>2014-05-06T19:15:48</dtePassed>
        <intScore>12345</intScore>
        <intPassingScore>12345</intPassingScore>
        <dteExpiration>2014-05-06T19:15:48</dteExpiration>
      </CRS>
    '''


class GRADEBOOK(TableDesign):
    date_format = None

    markup = '''
      <GRADEBOOK>
        <intCompletionReportID>12345</intCompletionReportID>
        <intInstitutionID>12345</intInstitutionID>
        <strCompletionReport>a</strCompletionReport>
        <intGroupID>12345</intGroupID>
        <strGroup>a</strGroup>
        <intStageID>12345</intStageID>
        <strStage>a</strStage>
      </GRADEBOOK>
    '''


class MEMBERS(TableDesign):
    date_format = '%m/%d/%y'

    markup = '''
      <MEMBERS>
        <intMemberID>12345</intMemberID>
        <strLastII>a</strLastII>
        <strFirstII>a</strFirstII>
        <strUsernameII>a</strUsernameII>
        <strInstUsername>a</strInstUsername>
        <strInstEmail>a</strInstEmail>
        <dteAdded>09/09/14</dteAdded>
        <dteAffiliated>09/09/14</dteAffiliated>
        <dteLastLogin>09/09/14</dteLastLogin>
        <strCustom1 />
        <strCustom2 />
        <strCustom3 />
        <strCustom4 />
        <strCustom5 />
        <strSSOCustomAttrib1 />
        <strSSOCustomAttrib2>a</strSSOCustomAttrib2>
        <strEmployeeNum />
      </MEMBERS>
    '''


class HSR(object):
    def __init__(self, db_name,
                 combo_view='hsr_training_combo'):
        self.db_name = db_name
        self.combo_view = combo_view
        log.info('HSR DB name: %s', db_name)

        meta = MetaData()

        for cls in [CRS, MEMBERS, GRADEBOOK]:
            cls.xml_table(meta, db_name)

        for _, name, date_col in Chalk.tables:
            Chalk.table(meta, db_name, name, date_col)

        Table(combo_view, meta,
              Column('username', String),
              Column('expired', DateTime),
              Column('completed', DateTime),
              Column('course', String),
              schema=db_name or None)

        self.tables = meta.tables

    def table(self, name):
        qname = ('%s.%s' % (self.db_name, name) if self.db_name
                 else name)
        return self.tables[qname]


class Chalk(TableDesign):
    '''Chalk back-fill data

        >>> with Mock().openf('i.csv') as infp:
        ...     records = relation.readRecords(infp)
        >>> records[0].CompleteDate
        '8/4/2012 0:00'

        >>> Chalk.parse_dates(records, ['CompleteDate'])[0].CompleteDate
        datetime.datetime(2012, 8, 4, 0, 0)
    '''
    date_format = '%m/%d/%Y %H:%M'

    tables = [('--full', 'HumanSubjectsFull', 'DateCompleted'),
              ('--refresher', 'HumanSubjectsRefresher', 'CompleteDate'),
              ('--in-person', 'HumanSubjectsInPerson', 'CompleteDate')]

    @classmethod
    def table(cls, meta, db_name, name, date_col):
        return Table(name, meta,
                     Column('FirstName', VARCHAR120),
                     Column('LastName', VARCHAR120),
                     Column('Email', VARCHAR120),
                     Column('EmployeeID', VARCHAR120),
                     Column(date_col, DateTime()),
                     Column('Username', VARCHAR120),
                     schema=db_name,
                     **redcapview.backend_options)


@maker
def TrainingRecordsRd(acct):
    '''
    >>> acct = (lambda: None, None, None)
    >>> rd = TrainingRecordsRd(acct)

    >>> print rd.lookup_query
    hsr_training_combo
    '''
    dbtrx, db_name, _ = acct
    hsr = HSR(db_name)
    lookup = hsr.table(hsr.combo_view)

    def __getitem__(_, instUserName):
        with dbtrx() as q:
            result = q.execute(
                lookup.select(lookup.c.username == instUserName)
                .order_by(lookup.c.expired.desc()))
            record = result.fetchone()

        if not record:
            raise KeyError(instUserName)

        return record

    return [__getitem__], dict(lookup_query=lookup)


@maker
def TrainingRecordsAdmin(acct, exempt_pid,
                         course_pattern='%Human Subjects Research%',
                         colSize=120):
    '''
    >>> acct = (lambda: Mock()._db.connect(), None, None)
    >>> ad = TrainingRecordsAdmin(acct, 0)

    .. note:: TODO: move this complex query into a view.

    >>> print ad.citi_query
    ... # doctest: +NORMALIZE_WHITESPACE
    SELECT "CRS"."InstitutionUserName" AS username,
           "CRS"."dteExpiration" AS expired,
           "CRS"."dtePassed" AS completed,
           "CRS"."strCompletionReport" AS course
    FROM "CRS"
    WHERE "CRS"."strCompletionReport" LIKE :strCompletionReport_1
    AND "CRS"."dteExpiration" IS NOT NULL

    >>> print ad.chalk_queries[0]
    ... # doctest: +NORMALIZE_WHITESPACE
    SELECT "full"."Username", year_after("full"."DateCompleted"),
           "full"."DateCompleted", 'HumanSubjectsFull'
    FROM "HumanSubjectsFull" AS "full"

    >>> hsr = HSR('')
    >>> [c.name for c in hsr.table(hsr.combo_view).columns]
    ['username', 'expired', 'completed', 'course']

    >>> print ad.query
    ... # doctest: +NORMALIZE_WHITESPACE +ELLIPSIS
    SELECT "CRS"."InstitutionUserName" ...
    FROM "CRS" ...
    UNION ALL
    SELECT username.value ...
    FROM redcap_data AS username, ...
    UNION ALL
    SELECT "full"."Username", ...
    FROM "HumanSubjectsFull" AS "full" ...
    '''
    dbtrx, db_name, redcapdb = acct
    hsr = HSR(db_name)
    crs = hsr.table('CRS')

    citi_query = (select([crs.c.InstitutionUserName.label('username'),
                          crs.c.dteExpiration.label('expired'),
                          crs.c.dtePassed.label('completed'),
                          crs.c.strCompletionReport.label('course')])
                  .where(and_(crs.c.strCompletionReport.like(course_pattern),
                              # != None is sqlalchemy-speak for is not null
                              crs.c.dteExpiration != None)))  # noqa
    chalk_queries = [select([t.c.Username, year_after(t.c[date_col]),
                             t.c[date_col], literal_column("'%s'" % name)])
                     for opt, name, date_col in Chalk.tables
                     for t in [hsr.table(name).alias(opt[2:])]]

    redcap_data = redcapview.in_schema(redcapdb, meta=MetaData())
    exempt_query = redcapview.unpivot(exempt_pid,
                                      [c.name for c in citi_query.c],
                                      redcap_data=redcap_data)

    who_when = union_all(citi_query, exempt_query,
                         *chalk_queries).alias('who_when')

    def docRecords(_, doc):
        name = iter(doc).next().tag
        tdef = hsr.table(name)
        records = relation.docToRecords(doc, [c.name for c in tdef.columns])
        return name, records

    def combine(_):
        log.info('creating view: %s', hsr.combo_view)
        combo = [DropView(hsr.combo_view, hsr.db_name),
                 CreateView(hsr.combo_view, who_when, hsr.db_name)]

        with dbtrx() as ddl:
            for stmt in combo:
                ddl.execute(stmt)

    def put(_, name, records):
        tdef = hsr.table(name)
        with dbtrx() as dml:
            log.info('(re-)creating %s', tdef.name)
            tdef.drop(dml, checkfirst=True)
            tdef.create(dml)
            dml.execute(tdef.insert(), [t._asdict() for t in records])
            log.info('inserted %d rows into %s', len(records), tdef.name)

    return [put, docRecords, combine], dict(
        course_pattern=course_pattern,
        citi_query=citi_query,
        chalk_queries=chalk_queries,
        query=who_when)


@maker
def CitiSOAPService(client, auth):
    '''CitiSOAPService

    ref https://webservices.citiprogram.org/SOAP/CITISOAPService.asmx
    '''
    methods = dict(
        GetCompletionReportsXML=client.GetCompletionReportsXML,
        GetGradeBooksXML=client.GetGradeBooksXML,
        GetMembersXML=client.GetMembersXML)

    def get(_, which):
        reply = auth(methods[which])
        markup = reply[which + 'Result']
        log.info('got length=%d from %s', len(markup), which)
        return XML(markup.encode('utf-8'))

    attrs = dict((name, name) for name in methods.keys())
    return [get], attrs


@maker
def CLI(argv, environ, openf, create_engine, SoapClient):
    # Don't require docopt except for command-line usage
    from docopt import docopt

    usage = __doc__.split('\n..')[0]
    opts = docopt(usage, argv=argv[1:])
    log.debug('docopt: %s', opts)

    def getRecords(_, opt):
        with openf(opts[opt]) as infp:
            return relation.readRecords(infp)

    def account(_, opt):
        env_key = opts[opt]
        u = make_url(environ[env_key])
        # leave off redcap schema prefix for testing
        redcapdb = (None if u.drivername == 'sqlite' else 'redcap')

        return conntrx(create_engine(u).connect()), u.database, redcapdb

    def auth(_, wrapped):
        usr = opts['--user']
        pwd = environ[opts['--pwenv']]
        return wrapped(usr=usr, pwd=pwd)

    def soapClient(_):
        wsdl = opts['--wsdl']
        log.info('getting SOAP client for %s', wsdl)
        client = SoapClient(wsdl=wsdl)
        return client

    attrs = dict((name.replace('--', ''), val)
                 for (name, val) in opts.iteritems())
    return [getRecords, auth, soapClient, account], attrs


class Mock(object):
    environ = dict(CITI_PASSWORD='sekret',
                   HSR_TRAIN_CHECK='sqlite://',
                   HSR_TRAIN_ADMIN='sqlite://')

    files = {
        'f.csv': (None, '''
FirstName,LastName,Email,EmployeeID,DateCompleted,Username
R,S,RS@example,J1,8/4/2011 0:00,rs
        '''.strip()),
        'i.csv': (None, '''
FirstName,LastName,Email,EmployeeID,CompleteDate,Username
R2,S,RS2@example,J1,8/4/2012 0:00,rs2
        '''.strip()),
        'r.csv': (None, '''
FirstName,LastName,Email,EmployeeID,CompleteDate,Username
R3,S,RS3@example,J1,8/4/2013 0:00,rs3
        '''.strip())}

    def __init__(self):
        import StringIO

        self._db = None  # set in cli_access()
        self.argv = []
        self._fs = dict(self.files)
        self.create_engine = lambda path: self._db
        self.SoapClient = lambda wsdl: self
        self.stdout = StringIO.StringIO()

    from contextlib import contextmanager

    @contextmanager
    def openf(self, path, mode='r'):
        import StringIO

        if mode == 'w':
            buf = StringIO.StringIO()
            self._fs[path] = (buf, None)
            try:
                yield buf
            finally:
                self._fs[path] = (None, buf.getvalue())
        else:
            _buf, content = self._fs[path]
            yield StringIO.StringIO(content)

    def cli_access(self, cmd, db=None):
        import pkg_resources as pkg
        from sqlalchemy import create_engine  # sqlite in-memory use only

        self.argv = cmd.split()

        # self._db = db = create_engine('sqlite:///mock.db')
        self._db = db = db or create_engine('sqlite://')
        if not ('--refresh' in self.argv
                or 'backfill' in self.argv
                or 'combine' in self.argv):
            cn = db.connect().connection
            cn.executescript(pkg.resource_string(__name__, 'test_cache.sql'))

        return lambda: CLI(self.argv, self.environ, self.openf,
                           self.create_engine, self.SoapClient)

    def _check(self, usr, pwd):
        if not (usr == 'MySchool' and
                pwd == self.environ['CITI_PASSWORD']):
            raise IOError

    def GetCompletionReportsXML(self, usr, pwd):
        self._check(usr, pwd)
        xml = relation.mock_xml_records(CRS.markup, 5)
        return dict(GetCompletionReportsXMLResult=xml)

    def GetGradeBooksXML(self, usr, pwd):
        self._check(usr, pwd)
        xml = relation.mock_xml_records(GRADEBOOK.markup, 3)
        return dict(GetGradeBooksXMLResult=xml)

    def GetMembersXML(self, usr, pwd):
        self._check(usr, pwd)
        xml = relation.mock_xml_records(MEMBERS.markup, 4)
        return dict(GetMembersXMLResult=xml)


if __name__ == '__main__':
    def _privileged_main():
        from __builtin__ import open as openf
        from os import environ
        from sys import argv, stdout

        from sqlalchemy import create_engine

        def access():
            logging.basicConfig(
                level=logging.DEBUG if '--debug' in argv else logging.INFO)
            if '--debug' in argv:
                logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

            # ew... after this import, basicConfig doesn't work
            from pysimplesoap.client import SoapClient

            return CLI(argv, environ, openf,
                       create_engine, SoapClient=SoapClient)

        main(stdout, access)

    _privileged_main()
