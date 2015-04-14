r'''traincheck -- check human subjects training records via CITI

Usage:
  traincheck [options] IDVAULT_NAME
  traincheck [options] --refresh

Options:
  --reports=FILE     completion reports cache file
                     [default: completionReports.xml]
  --gradebooks=FILE  gradebooks cache file
                     [default: gradebooks.xml]
  --members=FILE     member info cache file
                     [default: members.xml]
  --cache=FILE       cache DB file
                     [default: trainingRecords.db]
  --wsdl=URL         Service Description URL
                     [default: https://webservices.citiprogram.org/SOAP/CITISOAPService.asmx?WSDL]  # noqa
  --user=NAME        [default: KUMC_Citi]
  --pwenv=K          environment variable to look up password
                     [default: PASSWORD]
  --debug            turn on debug logging

.. note:: Usage doc stops here.


Scenario one::

    >>> from sys import stdout
    >>> s1 = Mock()

Let's refresh the cache from the CITI service::

    >>> main(stdout, s1.cli_access('traincheck --refresh'))

The cache is stored in the filesystem::

    >>> print '\n'.join(sorted(s1._fs.keys()))
    completionReports.xml
    gradebooks.xml
    members.xml
    trainingRecords.db

Now let's look up Bob's training::

    >>> main(stdout, s1.cli_access('traincheck bob'))
    ... # doctest: +NORMALIZE_WHITESPACE
    CRS(MemberID=u'123', intScore=u'96',
        strCompletionReport=u'Human Subjects Research',
        InstitutionUserName=u'bob')

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

from lalib import maker, dbmgr
import relation

log = logging.getLogger(__name__)

CITI_NAMESPACE = 'https://webservices.citiprogram.org/'


def main(stdout, access):
    cli = access()

    if cli.refresh:
        svc = CitiSOAPService(cli.soapClient(), cli.auth)

        for (opt, fn, k) in [
                # smallest to largest typical payload
                ('--gradebooks', cli.gradebooks, svc.GetGradeBooksXML),
                ('--members', cli.members, svc.GetMembersXML),
                ('--reports', cli.reports, svc.GetCompletionReportsXML)]:
            markup = svc.get(k)
            cli.put(opt, markup)
            log.info('saved length=%d to %s', len(markup), fn)
            try:
                records = relation.docToRecords(
                    ET.fromstring(markup.encode('utf-8')))
            except StopIteration:
                raise SystemExit('no records in %s' % fn)
            relation.put(cli.cacheDB(), records)
    else:
        store = TrainingRecordStore(cli.cacheDB())
        try:
            training = store[cli.IDVAULT_NAME]
        except KeyError:
            raise SystemExit('no training records for %s' % cli.IDVAULT_NAME)
        log.info('training OK: %s', training)
        stdout.write(str(training))


@maker
def TrainingRecordStore(
        dbtrx,
        course='Human Subjects Research',
        dql="""
        select CRS.*
        from CRS
        where CRS.strCompletionReport = ?
        and CRS.InstitutionUserName = ?
        limit 1
        """):
    '''
    >>> inert = TrainingRecordStore(dbtrx=None)
    >>> inert.course
    'TODO: double-check course name'

    '''
    def __getitem__(_, instUserName):
        with dbtrx() as q:
            q.execute(dql, (course, instUserName))
            CRS = relation.tableTuple('CRS', q.description)
            row = q.fetchone()

        if not row:
            raise KeyError(instUserName)

        return CRS(*row)

    return [__getitem__], dict(course=course)


@maker
def CitiSOAPService(client, auth):
    methods = dict(
        GetCompletionReportsXML=client.GetCompletionReportsXML,
        GetGradeBooksXML=client.GetGradeBooksXML,
        GetMembersXML=client.GetMembersXML)

    def get(_, which):
        reply = auth(methods[which])
        return reply[which + 'Result']

    attrs = dict((name, name) for name in methods.keys())
    return [get], attrs


@maker
def CLI(argv, environ, openf, connect, SoapClient):
    usage = __doc__.split('\n..')[0]
    opts = docopt(usage, argv=argv[1:])
    log.debug('docopt: %s', opts)

    usr = opts['--user']
    pwd = environ[opts['--pwenv']]

    def getBytes(_, opt):
        with openf(opts[opt]) as infp:
            return infp.read()

    def put(_, opt, content):
        with openf(opts[opt], 'w') as outfp:
            outfp.write(content.encode('utf-8'))

    def cacheDB(_):
        return dbmgr(lambda: connect(opts['--cache']))

    def auth(_, wrapped):
        return wrapped(usr=usr, pwd=pwd)

    def soapClient(_):
        wsdl = opts['--wsdl']
        log.info('getting SOAP client for %s', wsdl)
        client = SoapClient(wsdl=wsdl)
        return client

    attrs = dict((name.replace('--', ''), val)
                 for (name, val) in opts.iteritems())
    return [getBytes, put, auth, soapClient, cacheDB], attrs


class Mock(object):
    environ = dict(PASSWORD='sekret')

    def __init__(self):
        import StringIO

        self._db = None  # set in cli_access()
        self.argv = []
        self._fs = {}
        self.connect = lambda path: self._db
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
        import sqlite3
        import pkg_resources as pkg

        self.argv = cmd.split()
        opts = docopt(__doc__.split('\n.. ')[0], self.argv[1:])
        self._fs[opts['--cache']] = None

        # self._db = db = sqlite3.connect('mock.db')
        self._db = db = sqlite3.connect(':memory:')
        if not '--refresh' in self.argv:
            db.executescript(pkg.resource_string(__name__, 'test_cache.db'))

        return lambda: CLI(self.argv, self.environ, self.openf,
                           self.connect, self.SoapClient)

    def _check(self, pwd):
        if not pwd == self.environ['PASSWORD']:
            raise IOError

    CRS = """
    <NewDataSet>
      <CRS>
        <MemberID>123</MemberID>
        <intScore>96</intScore>
        <strCompletionReport>Human Subjects Research</strCompletionReport>
        <InstitutionUserName>bob</InstitutionUserName>
      </CRS>
      <CRS>
        <MemberID>124</MemberID>
        <intScore>91</intScore>
      </CRS>
    </NewDataSet>
    """

    def GetCompletionReportsXML(self, usr, pwd):
        self._check(pwd)
        return dict(GetCompletionReportsXMLResult=self.CRS)

    GRADEBOOK = """
    <NewDataSet>
      <GRADEBOOK>
        <intCompletionReportID>257</intCompletionReportID>
        <intInstitutionID>12</intInstitutionID>
        <strCompletionReport>Basic</strCompletionReport>
      </GRADEBOOK>
    </NewDataSet>
    """

    def GetGradeBooksXML(self, usr, pwd):
        self._check(pwd)
        return dict(GetGradeBooksXMLResult=self.GRADEBOOK)

    MEMBERS = """
    <NewDataSet>
      <MEMBERS>
        <intMemberID>43704</intMemberID>
        <strLastII>Able</strLastII>
        <strFirstII>Laurie</strFirstII>
        <strInstUsername>lable</strInstUsername>
        <strInstEmail>lable@example</strInstEmail>
      </MEMBERS>
    </NewDataSet>
    """

    def GetMembersXML(self, usr, pwd):
        self._check(pwd)
        return dict(GetMembersXMLResult=self.MEMBERS)


if __name__ == '__main__':
    def _privileged_main():
        from __builtin__ import open as openf
        from os import environ
        from sqlite3 import connect
        from sys import argv, stdout

        def access():
            logging.basicConfig(
                level=logging.DEBUG if '--debug' in argv else logging.INFO)

            # ew... after this import, basicConfig doesn't work
            from pysimplesoap.client import SoapClient

            return CLI(argv, environ, openf,
                       connect, SoapClient=SoapClient)

        main(stdout, access)

    _privileged_main()
