r'''traincheck -- check human subjects training records via CITI

Usage:
  traincheck [options] IDVAULT_NAME
  traincheck [options] --refresh

Options:
  --dbrd=NAME        environment variable with sqlalchemy URL of account
                     with read access to PII DB
                     [default: HSR_TRAIN_CHECK]
  --dbadmin=NAME     environment variable with sqlalchemy URL of account
                     with admin (create, delete, ...) access to PII DB
                     [default: HSR_TRAIN_ADMIN]
  --wsdl=URL         Service Description URL
                     [default: https://webservices.citiprogram.org/SOAP/CITISOAPService.asmx?WSDL]  # noqa
  --user=NAME        [default: KUMC_Citi]
  --pwenv=K          environment variable to look up password
                     [default: PASSWORD]
  --debug            turn on debug logging


PII DB is a database suitable for PII (personally identifiable information).

.. note:: Usage doc stops here.


Scenario one::

    >>> from sys import stdout
    >>> s1 = Mock()

Let's refresh the cache from the CITI service::

    >>> main(stdout, s1.cli_access('traincheck --refresh'))

The cache is stored in the database::

    >>> s1._db.execute('select count(*) from CRS').fetchall()
    [(5,)]

Now let's look up Bob's training::

    >>> main(stdout, s1.cli_access('traincheck bob'))
    ... # doctest: +NORMALIZE_WHITESPACE
    (None, 123, None, None, u'bob', None, None, None, None,
     u'Human Subjects Research', None, None, None, None,
     None, None, None, None, 96, None, None)

But there's no training on file for Fred::

    >>> main(stdout, s1.cli_access('traincheck fred'))
    Traceback (most recent call last):
      ...
    SystemExit: no training records for fred


    >>> 'TODO: check for expired training'
    ''

'''

import logging
import xml.etree.ElementTree as ET

from docopt import docopt
from sqlalchemy import (MetaData, Table, Column,
                        String, Integer, Date,
                        and_)
from sqlalchemy.engine.url import make_url

from lalib import maker
import relation

STRING_SIZE = 120
log = logging.getLogger(__name__)

CITI_NAMESPACE = 'https://webservices.citiprogram.org/'


def main(stdout, access):
    cli = access()

    if cli.refresh:
        svc = CitiSOAPService(cli.soapClient(), cli.auth)

        admin = TrainingRecordsAdmin(cli.account('--dbadmin'))
        for k in [
                # smallest to largest typical payload
                svc.GetGradeBooksXML,
                svc.GetMembersXML,
                svc.GetCompletionReportsXML]:
            doc = svc.get(k)
            try:
                admin.put(doc)
            except StopIteration:
                raise SystemExit('no records in %s' % k)
    else:
        store = TrainingRecordsRd(cli.account('--dbrd'))
        try:
            training = store[cli.IDVAULT_NAME]
        except KeyError:
            raise SystemExit('no training records for %s' % cli.IDVAULT_NAME)
        log.info('training OK: %s', training)
        stdout.write(str(training))


class CRS(object):
    # TODO: parse dates to avoid ...
    # Warning: Data truncated for column 'AddedMember' at row 34
    # or suppress the warning
    # Dates are actually of the form:
    # 2014-05-06T19:15:48.2-04:00
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
        <AddedMember>2014-05-06</AddedMember>
        <strCompletionReport>a</strCompletionReport>
        <intGroupID>12345</intGroupID>
        <strGroup>a</strGroup>
        <intStageID>12345</intStageID>
        <intStageNumber>12345</intStageNumber>
        <strStage>a</strStage>
        <intCompletionReportID>12345</intCompletionReportID>
        <intMemberStageID>12345</intMemberStageID>
        <dtePassed>2014-05-06</dtePassed>
        <intScore>12345</intScore>
        <intPassingScore>12345</intPassingScore>
        <dteExpiration>2014-05-06</dteExpiration>
      </CRS>
    '''


class GRADEBOOK(object):
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


class MEMBERS(object):
    # TODO: dteXXX fields are actually dates in 09/09/14 format.
    markup = '''
      <MEMBERS>
        <intMemberID>12345</intMemberID>
        <strLastII>a</strLastII>
        <strFirstII>a</strFirstII>
        <strUsernameII>a</strUsernameII>
        <strInstUsername>a</strInstUsername>
        <strInstEmail>a</strInstEmail>
        <dteAdded>a</dteAdded>
        <dteAffiliated>a</dteAffiliated>
        <dteLastLogin>a</dteLastLogin>
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
    def __init__(self,
                 db_name='hsr_cache'):
        self.db_name = db_name

        ty = lambda text: (
            Integer if text == '12345' else
            # For unit testing, avoid:
            # SQLite Date type only accepts Python date objects as input.
            # by just using string.
            Date() if db_name and text == '2014-05-06' else
            String(STRING_SIZE))

        columns = lambda markup: [
            Column(field.tag, ty(field.text))
            for field in ET.fromstring(markup)]

        meta = MetaData()

        for cls in [CRS, MEMBERS, GRADEBOOK]:
            Table(cls.__name__, meta, *columns(cls.markup),
                  schema=db_name)

        self.tables = meta.tables

    def table(self, name):
        qname = ('%s.%s' % (self.db_name, name) if self.db_name
                 else name)
        return self.tables[qname]


@maker
def TrainingRecordsRd(
        acct,
        course='Human Subjects Research'):
    '''
    >>> inert = TrainingRecordsRd(acct=(None, None))
    >>> inert.course
    'TODO: double-check course name'

    '''

    dbtrx, db_name = acct
    crs = HSR(db_name).table('CRS')

    def __getitem__(_, instUserName):
        with dbtrx() as q:
            result = q.execute(crs.select().where(
                and_(crs.c.strCompletionReport == course,
                     crs.c.InstitutionUserName == instUserName)))
            record = result.fetchone()

        if not record:
            raise KeyError(instUserName)

        return record

    return [__getitem__], dict(course=course)


@maker
def TrainingRecordsAdmin(acct,
                         colSize=120):
    dbtrx, db_name = acct
    hsr = HSR(db_name)

    def put(_, doc):
        name = iter(doc).next().tag
        tdef = hsr.table(name)
        records = relation.docToRecords(doc, [c.name for c in tdef.columns])
        records = [t._asdict() for t in records]
        with dbtrx() as dml:
            log.info('(re-)creating %s', tdef.name)
            tdef.drop(dml, checkfirst=True)
            tdef.create(dml)
            dml.execute(tdef.insert(), records)
            log.info('inserted %d rows into %s', len(records), tdef.name)

    return [put], {}


@maker
def CitiSOAPService(client, auth):
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

    usr = opts['--user']
    pwd = environ[opts['--pwenv']]

    def getBytes(_, opt):
        with openf(opts[opt]) as infp:
            return infp.read()

    def account(_, opt):
        env_key = opts[opt]
        u = make_url(environ[env_key])
        return lambda: create_engine(u).connect(), u.database

    def auth(_, wrapped):
        return wrapped(usr=usr, pwd=pwd)

    def soapClient(_):
        wsdl = opts['--wsdl']
        log.info('getting SOAP client for %s', wsdl)
        client = SoapClient(wsdl=wsdl)
        return client

    attrs = dict((name.replace('--', ''), val)
                 for (name, val) in opts.iteritems())
    return [getBytes, auth, soapClient, account], attrs


class Mock(object):
    environ = dict(PASSWORD='sekret',
                   HSR_TRAIN_CHECK='sqlite://',
                   HSR_TRAIN_ADMIN='sqlite://')

    def __init__(self):
        import StringIO

        self._db = None  # set in cli_access()
        self.argv = []
        self._fs = {}
        self.create_engine = lambda path: self._db
        self.SoapClient = lambda wsdl: self
        self.stdout = StringIO.StringIO()

    from contextlib import contextmanager

    @contextmanager
    def openf(self, path, mode):
        import StringIO

        if mode == 'w':
            buf = StringIO.StringIO()
            self._fs[path] = (buf, None)
            try:
                yield buf
            finally:
                self._fs[path] = (None, buf.getvalue())
        else:
            raise IOError(path)

    def cli_access(self, cmd):
        import pkg_resources as pkg
        from sqlalchemy import create_engine  # sqlite in-memory use only

        self.argv = cmd.split()

        # self._db = db = create_engine('sqlite:///mock.db')
        self._db = db = create_engine('sqlite://')
        if not '--refresh' in self.argv:
            cn = db.connect().connection
            cn.executescript(pkg.resource_string(__name__, 'test_cache.sql'))

        return lambda: CLI(self.argv, self.environ, self.openf,
                           self.create_engine, self.SoapClient)

    def _check(self, pwd):
        if not pwd == self.environ['PASSWORD']:
            raise IOError

    @classmethod
    def xml_records(self, template, qty):
        from datetime import date

        n = [10]

        def num():
            n[0] += 17
            return n[0]

        def dt():
            n[0] += 29
            return date(2000, n[0] % 12 + 1, n[0] * 3 % 27)

        def txt():
            n[0] += 13
            return 's' * (n[0] % 5) + 't' * (n[0] % 7)

        def record_markup():
            record = ET.fromstring(template)
            for field in record:
                if field.text == '12345':
                    field.text = str(num())
                elif field.text == '2014-05-06':
                    field.text = str(dt())
                else:
                    field.text = txt()

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
