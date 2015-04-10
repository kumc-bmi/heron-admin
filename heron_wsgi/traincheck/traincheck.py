'''traincheck -- check human subjects training records via CITI

WORK IN PROGRESS. NOT YET FUNCTIONAL.

Usage:
  traincheck [options] members
  traincheck [options] gradebooks
  traincheck [options] <username>

Options:
  --wsdl=URL      Service Description URL
                  [default: https://webservices.citiprogram.org/SOAP/CITISOAPService.asmx?WSDL]  # noqa
  --user=NAME     [default: KUMC_Citi]
  --pwenv=K       environment variable to look up password [default: PASSWORD]
'''

import logging

from docopt import docopt

from lalib import maker

log = logging.getLogger(__name__)

CITI_NAMESPACE = 'https://webservices.citiprogram.org/'


def main(stdout, access):
    cli = access()

    training_records = CitiSOAPService(cli.soapClient(), cli.auth)

    if cli.members:
        markup = training_records.membersXML()
        stdout.write(markup)
    elif cli.gradebooks:
        markup = training_records.gradeBooksXML()
        stdout.write(markup)
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
def CLI(argv, environ, SoapClient):
    opts = docopt(__doc__, argv=argv[1:])

    usr = opts['--user']
    pwd = environ[opts['--pwenv']]

    def auth(_, wrapped):
        def method(**kwargs):
            return wrapped(usr=usr, pwd=pwd, **kwargs)

        return method

    def soapClient(_):
        client = SoapClient(wsdl=opts['--wsdl'])
        log.info('client: %s', client)
        return client

    return [auth, soapClient], opts


if __name__ == '__main__':
    def _privileged_main():
        from sys import argv, stdout
        from os import environ

        def access():
            logging.basicConfig(level=logging.INFO)

            # ew... after this import, basicConfig doesn't work
            from pysimplesoap.client import SoapClient

            return CLI(argv, environ, SoapClient)

        main(stdout, access)

    _privileged_main()
