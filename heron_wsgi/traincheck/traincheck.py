r'''traincheck -- check human subjects training records via CITI

Usage:
  traincheck [options] IDVAULT_NAME
  traincheck [options] --refresh --user=NAME
  traincheck [options] backfill --full=FILE --refresher=FILE --in-person=FILE

Options:
  --dbrd=NAME        environment variable with sqlalchemy URL of account
                     with read access to PII DB
                     [default: HSR_TRAIN_CHECK]
  --dbadmin=NAME     environment variable with sqlalchemy URL of account
                     with admin (create, delete, ...) access to PII DB
                     [default: HSR_TRAIN_ADMIN]
  --wsdl=URL         Service Description URL
                     [default: https://webservices.citiprogram.org/SOAP/CITISOAPService.asmx?WSDL]  # noqa
  --user=NAME        username for login to CitiSOAPService
  --pwenv=K          environment variable to look up password
                     [default: CITI_PASSWORD]
  --debug            turn on debug logging


PII DB is a database suitable for PII (personally identifiable information).

.. note:: Usage doc stops here.


Scenario one::

    >>> from sys import stdout
    >>> s1 = Mock()

Let's refresh the cache from the CITI service::

    >>> main(stdout, s1.cli_access('traincheck --refresh --user=MySchool'))

The cache is stored in the database::

    >>> s1._db.execute('select count(*) from CRS').fetchall()
    [(5,)]

Now let's backfill chalk records::

    >>> main(stdout, s1.cli_access(
    ...     'traincheck backfill '
    ...          '--full=f.csv --refresher=r.csv --in-person=i.csv',
    ...     db=s1._db))

    >>> a = s1._db.execute('select * from HumanSubjectsRefresher')
    >>> [zip(a.keys(), r) for r in a.fetchall()]
    ... # doctest: +NORMALIZE_WHITESPACE
    [[(u'FirstName', u'R3'), (u'LastName', u'S'),
      (u'Email', u'RS3@example'), (u'EmployeeID', u'J1'),
      (u'CompleteDate', u'2013-08-04 00:00:00.000000'),
      (u'Username', u'rs3')]]

Now let's look up Bob's training::

    >>> rd = TrainingRecordsRd(acct=(lambda: s1._db.connect(), None))
    >>> rd.course_pattern
    '%Human Subjects Research%'

    >>> rd['sssstttt'].expired
    datetime.datetime(2000, 2, 4, 12, 34, 56)

But there's no training on file for Fred::

    >>> rd['fred']
    Traceback (most recent call last):
      ...
    KeyError: 'fred'

'''

import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

from docopt import docopt
from sqlalchemy import (MetaData, Table, Column,
                        String, Integer, Date, DateTime,
                        select, union_all,
                        and_)
from sqlalchemy.engine.url import make_url

from lalib import maker
import relation

VARCHAR120 = String(120)
log = logging.getLogger(__name__)

CITI_NAMESPACE = 'https://webservices.citiprogram.org/'


def main(stdout, access):
    cli = access()

    if cli.refresh:
        svc = CitiSOAPService(cli.soapClient(), cli.auth)

        admin = TrainingRecordsAdmin(cli.account('--dbadmin'))
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
        admin = TrainingRecordsAdmin(cli.account('--dbadmin'))
        for (opt, table_name, date_col) in Chalk.tables:
            data = cli.getRecords(opt)
            admin.put(table_name, Chalk.parse_dates(data, [date_col]))
    else:
        store = TrainingRecordsRd(cli.account('--dbrd'))
        try:
            training = store[cli.IDVAULT_NAME]
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
                for field in ET.fromstring(cls.markup)]

    @classmethod
    def xml_table(cls, meta, db_name):
        return Table(cls.__name__, meta,
                     *cls.columns(),
                     schema=db_name)


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
    def __init__(self, db_name):
        self.db_name = db_name
        log.info('HSR DB name: %s', db_name)

        meta = MetaData()

        for cls in [CRS, MEMBERS, GRADEBOOK]:
            cls.xml_table(meta, db_name)

        for _, name, date_col in Chalk.tables:
            Chalk.table(meta, db_name, name, date_col)

        self.tables = meta.tables

    def table(self, name):
        qname = ('%s.%s' % (self.db_name, name) if self.db_name
                 else name)
        return self.tables[qname]


class Chalk(TableDesign):
    '''Chalk back-fill data

        >>> with Mock().openf('i.csv') as infp:
        ...     records = relation.readRecords(infp)
        >>> Chalk.parse_dates(records, ['CompleteDate'])
        ... # doctest: +NORMALIZE_WHITESPACE
        [R(FirstName='R2', LastName='S', Email='RS2@example', EmployeeID='J1',
         CompleteDate=datetime.datetime(2012, 8, 4, 0, 0), Username='rs2')]
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
                     schema=db_name)


@maker
def TrainingRecordsRd(
        acct,
        course_pattern='%Human Subjects Research%'):
    '''
    >>> acct = (lambda: Mock()._db.connect(), None)
    >>> rd = TrainingRecordsRd(acct)

    >>> print rd.citi_query
    ... # doctest: +NORMALIZE_WHITESPACE
    SELECT "CRS"."InstitutionUserName" AS username,
           "CRS"."dteExpiration" AS expired
    FROM "CRS"
    WHERE "CRS"."strCompletionReport" LIKE :strCompletionReport_1

    >>> print rd.chalk_queries[0]
    ... # doctest: +NORMALIZE_WHITESPACE
    SELECT "full"."Username",
           "full"."DateCompleted" + :DateCompleted_1 AS anon_1
    FROM "HumanSubjectsFull" AS "full"

    >>> print rd.query
    ... # doctest: +NORMALIZE_WHITESPACE
    SELECT "CRS"."InstitutionUserName" AS username,
           "CRS"."dteExpiration" AS expired
    FROM "CRS"
    WHERE "CRS"."strCompletionReport" LIKE :strCompletionReport_1
    UNION ALL
    SELECT "full"."Username",
           "full"."DateCompleted" + :DateCompleted_1 AS anon_1
    FROM "HumanSubjectsFull" AS "full"
    UNION ALL
    SELECT refresher."Username",
           refresher."CompleteDate" + :CompleteDate_1 AS anon_2
    FROM "HumanSubjectsRefresher" AS refresher
    UNION ALL
    SELECT "in-person"."Username",
           "in-person"."CompleteDate" + :CompleteDate_2 AS anon_3
    FROM "HumanSubjectsInPerson" AS "in-person"

    '''
    dbtrx, db_name = acct
    hsr = HSR(db_name)
    crs = hsr.table('CRS')

    year = timedelta(days=365.25)
    citi_query = (select([crs.c.InstitutionUserName.label('username'),
                          crs.c.dteExpiration.label('expired')])
                  .where(crs.c.strCompletionReport.like(course_pattern)))
    chalk_queries = [select([t.c.Username, t.c[date_col] + year])
                     for opt, name, date_col in Chalk.tables
                     for t in [hsr.table(name).alias(opt[2:])]]

    who_when = union_all(citi_query, *chalk_queries).alias('who_when')

    def __getitem__(_, instUserName):
        with dbtrx() as q:
            result = q.execute(who_when.select(
                who_when.c.username == instUserName))
            record = result.fetchone()

        if not record:
            raise KeyError(instUserName)

        return record

    return [__getitem__], dict(course_pattern=course_pattern,
                               citi_query=citi_query,
                               chalk_queries=chalk_queries,
                               query=who_when)


@maker
def TrainingRecordsAdmin(acct,
                         colSize=120):
    dbtrx, db_name = acct
    hsr = HSR(db_name)

    def docRecords(_, doc):
        name = iter(doc).next().tag
        tdef = hsr.table(name)
        records = relation.docToRecords(doc, [c.name for c in tdef.columns])
        return name, records

    def put(_, name, records):
        tdef = hsr.table(name)
        with dbtrx() as dml:
            log.info('(re-)creating %s', tdef.name)
            tdef.drop(dml, checkfirst=True)
            tdef.create(dml)
            dml.execute(tdef.insert(), [t._asdict() for t in records])
            log.info('inserted %d rows into %s', len(records), tdef.name)

    return [put, docRecords], {}


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
        return ET.fromstring(markup.encode('utf-8'))

    attrs = dict((name, name) for name in methods.keys())
    return [get], attrs


@maker
def CLI(argv, environ, openf, create_engine, SoapClient):
    usage = __doc__.split('\n..')[0]
    opts = docopt(usage, argv=argv[1:])
    log.debug('docopt: %s', opts)

    def getBytes(_, opt):
        with openf(opts[opt]) as infp:
            return infp.read()

    def getRecords(_, opt):
        with openf(opts[opt]) as infp:
            return relation.readRecords(infp)

    def account(_, opt):
        env_key = opts[opt]
        u = make_url(environ[env_key])
        return lambda: create_engine(u).connect(), u.database

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
    return [getBytes, getRecords, auth, soapClient, account], attrs


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
        if not ('--refresh' in self.argv or 'backfill' in self.argv):
            cn = db.connect().connection
            cn.executescript(pkg.resource_string(__name__, 'test_cache.sql'))

        return lambda: CLI(self.argv, self.environ, self.openf,
                           self.create_engine, self.SoapClient)

    def _check(self, pwd):
        if not pwd == self.environ['CITI_PASSWORD']:
            raise IOError

    @classmethod
    def xml_records(self, template, qty):
        n = [10]

        def num():
            n[0] += 17
            return n[0]

        def ymd():
            n[0] += 29
            return '%04d-%02d-%02dT12:34:56' % (
                2000, n[0] % 12 + 1, (n[0] * 3) % 26 + 1)

        def mdy():
            n[0] += 29
            return '%02d/%02d/%02d' % (
                n[0] % 12 + 1, (n[0] * 3) % 26 + 1, 11)

        def txt(tag):
            n[0] += 13
            return (
                'Basic/Refresher Course - Human Subjects Research'
                if tag == 'strCompletionReport' and n[0] % 3
                else 's' * (n[0] % 5) + 't' * (n[0] % 7))

        def record_markup():
            record = ET.fromstring(template)
            for field in record:
                if field.text == '12345':
                    field.text = str(num())
                elif field.text == '2014-05-06T19:15:48':
                    field.text = ymd()
                elif field.text == '09/09/14':
                    field.text = mdy()
                else:
                    field.text = txt(field.tag)

            return ET.tostring(record)

        return ("<NewDataSet>"
                + '\n'.join(record_markup()
                            for _ in range(qty))
                + "</NewDataSet>")

    def GetCompletionReportsXML(self, usr, pwd):
        self._check(pwd)
        xml = self.xml_records(CRS.markup, 5)
        return dict(GetCompletionReportsXMLResult=xml)

    def GetGradeBooksXML(self, usr, pwd):
        self._check(pwd)
        xml = self.xml_records(GRADEBOOK.markup, 3)
        return dict(GetGradeBooksXMLResult=xml)

    def GetMembersXML(self, usr, pwd):
        self._check(pwd)
        xml = self.xml_records(MEMBERS.markup, 4)
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

            # ew... after this import, basicConfig doesn't work
            from pysimplesoap.client import SoapClient

            return CLI(argv, environ, openf,
                       create_engine, SoapClient=SoapClient)

        main(stdout, access)

    _privileged_main()
