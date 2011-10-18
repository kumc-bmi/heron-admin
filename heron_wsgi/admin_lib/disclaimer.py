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

import config
from db_util import mysql_connect
import redcapdb
from orm_base import Base

DISCLAIMERS_SECTION='disclaimers'
ACKNOWLEGEMENTS_SECTION='disclaimer_acknowledgements'


class Disclaimer(object):
    fields = ('disclaimer_id', 'url', 'current')

    def __repr__(self):
        return 'Disclaimer%s' % (
            (self.disclaimer_id, self.url, self.current),)

    def content(self, ua):
        r'''
           >>> d = Disclaimer()
           >>> d.url = 'http://example/'
           >>> d.content(_TestUrlOpener())
           ('<div id="blog-main">\n<h1 class="blog-title">headline</h1>main blog copy...\n</div>\n...\n', 'headline')
        '''
        body = ua.open(self.url).read()
        kludge = StringIO.StringIO(body.replace('&larr;', ''
                                                ).replace('&rarr;', '')
                                   )  #KLUDGE
        elt = etree.parse(kludge).xpath('//*[@id="blog-main"]')[0]
        headline = elt.xpath('.//*[@class="blog-title"]/text()')[0]

        return etree.tostring(elt), headline

_test_doc='''
<!DOCTYPE html>
<html><head><title>...</title></head>
<body>
...
<div id='blog-main'>
<h1 class='blog-title'>headline</h1>main blog copy...
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

    def __repr__(self):
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
            return rt

        drt = bind_options('project_id'.split(),
                           DISCLAIMERS_SECTION)
        redcapdb.redcap_eav_map(pid=drt.project_id,
                                cls=Disclaimer, fields=Disclaimer.fields,
                                alias='disclaimers')
        art = bind_options('project_id token'.split(),
                           ACKNOWLEGEMENTS_SECTION)
        redcapdb.redcap_eav_map(pid=art.project_id,
                                cls=Acknowledgement, fields=Acknowledgement.fields,
                                alias='acknowledgement')

    @classmethod
    def mods(cls, ini):
        return redcapdb.RunTime.mods(ini) + [cls(ini)]

    @classmethod
    def make(cls, ini, what=(sqlalchemy.engine.base.Connectable, redcapdb.CONFIG_SECTION)):
        depgraph = injector.Injector(cls.mods(ini))
        return depgraph.get(what)


if __name__ == '__main__':
    engine = RunTime.make('integration-test.ini')

    Base.metadata.bind = engine
    sm = sessionmaker(engine)
    s = sm()

    print "all disclaimers:"
    for d in s.query(Disclaimer):
        print d

    print 'all acknowledgements:'
    for ack in s.query(Acknowledgement):
        print ack

    print "current disclaimer and content:"
    for d in s.query(Disclaimer).filter(Disclaimer.current==1):
        print d
        print d.content(urllib2.build_opener())
