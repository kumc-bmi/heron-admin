'''traincheck -- check human subjects training records via CITI

WORK IN PROGRESS. NOT YET FUNCTIONAL.

Usage:
  traincheck [options] <username>
  traincheck [options] --refresh

Options:
  --members=FILE     member info cache file [default: members.xml]
  --gradebooks=FILE  gradebooks cache file [default: gradebooks.xml]
  --wsdl=URL         Service Description URL
                     [default: https://webservices.citiprogram.org/SOAP/CITISOAPService.asmx?WSDL]  # noqa
  --user=NAME        [default: KUMC_Citi]
  --pwenv=K          environment variable to look up password
                     [default: PASSWORD]
  --debug            turn on debug logging
'''

import logging

from docopt import docopt

from lalib import maker

log = logging.getLogger(__name__)

CITI_NAMESPACE = 'https://webservices.citiprogram.org/'


def main(stdout, access):
    cli = access()

    training_records = CitiSOAPService(cli.soapClient(), cli.auth)

    if cli.refresh:
        markup = training_records.membersXML()
        cli.wr('--members').write(markup)
        log.info('saved length=%d to %s', len(markup), cli.members)

        markup = training_records.gradeBooksXML()
        cli.wr('--gradebooks').write(markup)
        log.info('saved length=%d to %s', len(markup), cli.gradebooks)

    else:
        raise NotImplementedError


@maker
def CitiSOAPService(client, auth):
    GetMembersXML = auth(client.GetMembersXML)
    GetGradeBooksXML = auth(client.GetGradeBooksXML)

    def gradeBooksXML(_):
        reply = GetGradeBooksXML()
        return reply['GetGradeBooksXMLResult']

    def membersXML(_):
        reply = GetMembersXML()
        return reply['GetMembersXMLResult']

    return [gradeBooksXML, membersXML], {}


@maker
def CLI(argv, environ, openwr, SoapClient):
    opts = docopt(__doc__, argv=argv[1:])
    log.debug('docopt: %s', opts)

    usr = opts['--user']
    pwd = environ[opts['--pwenv']]

    def wr(_, opt):
        return openwr(opts[opt])

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
    return [wr, auth, soapClient], attrs


if __name__ == '__main__':
    def _privileged_main():
        from __builtin__ import open as openf
        from sys import argv, stdout
        from os import environ

        def access():
            logging.basicConfig(
                level=logging.DEBUG if '--debug' in argv else logging.INFO)

            # ew... after this import, basicConfig doesn't work
            from pysimplesoap.client import SoapClient

            return CLI(argv, environ,
                       openwr=lambda path: openf(path, 'w'),
                       SoapClient=SoapClient)

        main(stdout, access)

    _privileged_main()
