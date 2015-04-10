'''traincheck -- check human subjects training records via CITI

WORK IN PROGRESS. NOT YET FUNCTIONAL.

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
'''

import logging
import xml.etree.ElementTree as ET

from docopt import docopt

from lalib import maker, dbmgr
import relation

log = logging.getLogger(__name__)

CITI_NAMESPACE = 'https://webservices.citiprogram.org/'


def main(access):
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
            relation.docToTable(cli.cacheDB(),
                                ET.fromstring(markup.encode('utf-8')))
    else:
        who = cli.IDVAULT_NAME
        [reportsXML, gradeBooksXML, membersXML] = [
            cli.getBytes(opt)
            for opt in ['--reports', '--gradebooks', '--members']]
        store = TrainingRecordStore(reportsXML, gradeBooksXML, membersXML)
        when = store[who]
        log.info('records of %s good thru %s', who, when)


@maker
def TrainingRecordStore(reportsXML, gradeBooksXML, membersXML,
                        course='Human Subjects Research'):
    reports = ET.fromstring(reportsXML)
    members = ET.fromstring(membersXML)

    def memberLookup(instUserName):
        detail = (mElt for mElt in members.findall('MEMBERS')
                  if mElt.find('strInstUsername').text == instUserName).next()
        return detail.find('intMemberID').text

    def __getitem__(_, instUserName):
        memberID = memberLookup(instUserName)

        detail = (cElt for cElt in reports.findall('CRS')
                  if cElt.find('MemberID').text == memberID
                  and cElt.find('strCompletionReport').text == course).next()

        return detail.find('dteExpiration').text

    return [__getitem__], {}


@maker
def CitiSOAPService(client, auth):
    methods = dict(
        GetCompletionReportsXML=client.GetCompletionReportsXML,
        GetGradeBooksXML=client.GetGradeBooksXML,
        GetMembersXML=client.GetMembersXML)

    def get(_, which):
        reply = auth(methods[which])()
        return reply[which + 'Result']

    attrs = dict((name, name) for name in methods.keys())
    return [get], attrs


@maker
def CLI(argv, environ, openf, connect, SoapClient):
    opts = docopt(__doc__, argv=argv[1:])
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
        def method(**kwargs):
            return wrapped(usr=usr, pwd=pwd, **kwargs)

        return method

    def soapClient(_):
        wsdl = opts['--wsdl']
        log.info('getting SOAP client for %s', wsdl)
        client = SoapClient(wsdl=wsdl)
        return client

    attrs = dict((name.replace('--', ''), val)
                 for (name, val) in opts.iteritems())
    return [getBytes, put, auth, soapClient, cacheDB], attrs


if __name__ == '__main__':
    def _privileged_main():
        from __builtin__ import open as openf
        from os import environ
        from sqlite3 import connect
        from sys import argv

        def access():
            logging.basicConfig(
                level=logging.DEBUG if '--debug' in argv else logging.INFO)

            # ew... after this import, basicConfig doesn't work
            from pysimplesoap.client import SoapClient

            return CLI(argv, environ, openf,
                       connect, SoapClient=SoapClient)

        main(access)

    _privileged_main()
