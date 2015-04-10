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

from lalib import maker

log = logging.getLogger(__name__)

CITI_NAMESPACE = 'https://webservices.citiprogram.org/'


def main(access):
    cli = access()

    if cli.refresh:
        svc = CitiSOAPService(cli.soapClient(), cli.auth)

        for (opt, fn, k) in [
                ('--reports', cli.reports, svc.GetCompletionReportsXML),
                ('--gradebooks', cli.gradebooks, svc.GetGradeBooksXML),
                ('--members', cli.members, svc.GetMembersXML)]:
            markup = svc.get(k)
            cli.put(opt, markup)
            log.info('saved length=%d to %s', len(markup), fn)

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
def CLI(argv, environ, openf, SoapClient):
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

    def auth(_, wrapped):
        def method(**kwargs):
            return wrapped(usr=usr, pwd=pwd, **kwargs)

        return method

    def soapClient(_):
        client = SoapClient(wsdl=opts['--wsdl'])
        log.info('client: %s', client)
        return client

    attrs = dict((name.replace('--', ''), val)
                 for (name, val) in opts.iteritems())
    return [getBytes, put, auth, soapClient], attrs


if __name__ == '__main__':
    def _privileged_main():
        from __builtin__ import open as openf
        from sys import argv
        from os import environ

        def access():
            logging.basicConfig(
                level=logging.DEBUG if '--debug' in argv else logging.INFO)

            # ew... after this import, basicConfig doesn't work
            from pysimplesoap.client import SoapClient

            return CLI(argv, environ, openf, SoapClient=SoapClient)

        main(access)

    _privileged_main()
