'''disclaimer -- access disclaimers and acknowledgements from REDCap EAV DB
'''

import StringIO

# from pypi
import injector
from injector import inject, provides
from lxml import etree
import urllib2
import sqlalchemy
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import DeclarativeMeta

import config
from db_util import mysql_connect
import redcapdb

DISCLAIMERS_SECTION='disclaimers'
ACKNOWLEGEMENTS_SECTION='disclaimer_acknowledgements'


class Disclaimer(object):
    fields = ('disclaimer_id', 'url', 'current')

    def __str__(self):
        return 'Disclaimer%s' % (
            (self.disclaimer_id, self.url, self.current),)

    def content(self, ua):
        r'''
           >>> d = Disclaimer()
           >>> d.url = 'http://example/'
           >>> d.content(_TestUrlOpener())
           '<div id="blog-main">\nmain blog copy...\n</div>\n...\n'
        '''
        body = ua.open(self.url).read()
        kludge = StringIO.StringIO(body.replace('&larr;', ''
                                                ).replace('&rarr;', '')
                                   )  #KLUDGE
        elt = etree.parse(kludge).xpath('//*[@id="blog-main"]')[0]
        return etree.tostring(elt)

_test_doc='''
<!DOCTYPE html>
<html><head><title>...</title></head>
<body>
...
<div id='blog-main'>
main blog copy...
</div>
...
</body>
</html>
'''

class _TestUrlOpener(object):
    def open(self, addr):
        return StringIO.StringIO(_test_doc)


class Acknowledgement(object):
    fields = ('timestamp', 'user_id', 'disclaimer_address')

    def __str__(self):
        return 'Acknowledgement%s' % (
            (self.timestamp, self.user_id, self.disclaimer_address),)


class RunTime(injector.Module):
    def __init__(self, ini):
        self._ini = ini

    def configure(self, binder):
        def bind_options(names, section):
            rt = config.RuntimeOptions(names)
            rt.load(self._ini, section)
            binder.bind((config.Options, section), rt)

        bind_options('project_id'.split(),
                     DISCLAIMERS_SECTION)
        bind_options('token'.split(),
                     ACKNOWLEGEMENTS_SECTION)

    @provides(DeclarativeMeta)
    @inject(drt=(config.Options, DISCLAIMERS_SECTION))
    def mappings(self, drt):
        redcapdb.redcap_eav_map(pid=drt.project_id,
                                cls=Disclaimer, fields=Disclaimer.fields, alias='disclaimers')
        return redcapdb.Base

    @classmethod
    def mods(cls, ini):
        return redcapdb.RunTime.mods(ini) + [cls(ini)]

    @classmethod
    def make_stuff(cls, ini):
        depgraph = injector.Injector(cls.mods(ini))
        base = depgraph.get(DeclarativeMeta)
        ds = depgraph.get((sqlalchemy.engine.base.Connectable, redcapdb.CONFIG_SECTION))
        return ds, base


if __name__ == '__main__':
    engine, base = RunTime.make_stuff('integration-test.ini')

    base.metadata.bind = engine
    sm = sessionmaker(engine)
    s = sm()

    print "all disclaimers:"
    for d in s.query(Disclaimer):
        print d

    print "current disclaimer and content:"
    for d in s.query(Disclaimer).filter(Disclaimer.current==1):
        print d
        print d.content(urllib2.build_opener())
