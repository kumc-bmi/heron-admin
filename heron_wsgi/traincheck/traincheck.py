'''traincheck -- check human subjects training records via CITI

WORK IN PROGRESS. NOT YET FUNCTIONAL.

Usage:
  traincheck [options] <username>

Options:
  --wsdl=URL      Service Description URL
                  [default: https://webservices.citiprogram.org/SOAP/CITISOAPService.asmx?WSDL]  # noqa
  --user=NAME     [default: KUMC_Citi]
  --pwenv=K       environment variable to look up password [default: PASSWORD]
'''

import logging

from docopt import docopt

log = logging.getLogger(__name__)

CITI_NAMESPACE = 'https://webservices.citiprogram.org/'


def main(access, environ):
    # TODO: reduce the scope of environ, i.e. password
    cli, client = access()

    log.info('client: %s', client)
    log.info('CITISOAPService.HelloWorld(): %s', client.HelloWorld())

    usr = cli['--user']
    pwd = environ[cli['--pwenv']]

    x = client.HelloWorldbyUser(usr=usr, pwd=pwd)
    log.info('byUser: %s', x)

    reports = client.GetCompletionReports(usr=usr, pwd=pwd)
    log.info('reports: %s', reports)

    # import pdb; pdb.set_trace()
    raise NotImplementedError


if __name__ == '__main__':
    def _privileged_main():
        from sys import argv
        from os import environ

        cliCache = []

        def access():
            cli = docopt(__doc__, argv=argv[1:])
            cliCache.append(cli)

            logging.basicConfig(level=logging.INFO)

            # ew... after this import, basicConfig doesn't work
            from pysimplesoap.client import SoapClient

            return cli, SoapClient(wsdl=cli['--wsdl'])

        main(access, environ)

    _privileged_main()
