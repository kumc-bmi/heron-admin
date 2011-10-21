'''disclaimer -- access disclaimers and acknowledgements from REDCap EAV DB

:class:`Disclaimer` and :class:`Acknowledgement` provide read-only access via SQL queries.
:class:`AcknowledgementsProject`: supports adding records via the REDCap API.

Let's get a sessionmaker and an AcknowledgementsProject, which causes the database to get set up::

  >>> smaker, acksproj = Mock.make_stuff('', stuff=(
  ...       (sqlalchemy.orm.session.Session, redcapdb.CONFIG_SECTION),
  ...        AcknowledgementsProject))
  >>> s = smaker()
  >>> for row in s.execute(redcapdb.redcap_data.select()).fetchall():
  ...     print row
  (123, 1, u'1', u'disclaimer_id', u'1')
  (123, 1, u'1', u'url', u'http://example/blog/item/heron-release-xyz')
  (123, 1, u'1', u'current', u'1')

Now note the mapping to the Disclaimer class::

  >>> s.query(Disclaimer).all()
  [Disclaimer(disclaimer_id=1, url=http://example/blog/item/heron-release-xyz, current=1)]

'''

# python stdlib http://docs.python.org/library/
import StringIO
import csv
import datetime
import logging
import urllib
import urllib2
import uuid
import types
from xml.dom.minidom import parse

# from pypi
import injector
from injector import inject, provides, singleton
import sqlalchemy
from sqlalchemy.orm import sessionmaker
import xpath  # py-dom-xpath-0.1.tar.gz 4bbca5671245421e93ef2c1ea4e6e36810ccecbc

# from this package
import config
import redcapdb
from orm_base import Base

DISCLAIMERS_SECTION='disclaimers'
ACKNOWLEGEMENTS_SECTION='disclaimer_acknowledgements'
KTimeSource = injector.Key('TimeSource')

log = logging.getLogger(__name__)


class Disclaimer(redcapdb.REDCapRecord):
    fields = ('disclaimer_id', 'url', 'current')

    def content(self, ua):
        r'''
           >>> d = Disclaimer()
           >>> d.url = 'http://example/'
           >>> d.content(_TestUrlOpener())
           (u'<div id="blog-main">\n<h1 class="blog-title">headline</h1>main blog copy...\n</div>', u'headline')
        '''
        body = ua.open(self.url).read()
        kludge = StringIO.StringIO(body.replace('&larr;', ''
                                                ).replace('&rarr;', '')
                                   )  #KLUDGE
        elt = xpath.findnode('//*[@id="blog-main"]', parse(kludge))
        headline = xpath.findvalue('.//*[@class="blog-title"]/text()', elt)

        return elt.toxml(), headline

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


class Acknowledgement(redcapdb.REDCapRecord):
    fields = ('ack', 'timestamp', 'user_id', 'disclaimer_address')


class AcknowledgementsProject(object):
    '''AcknowledgementsProject serves as a REDCap API proxy for adding Acknowledgement records.
    '''
    @inject(rt=(config.Options, ACKNOWLEGEMENTS_SECTION),
            ua=urllib.URLopener,
            timesrc=KTimeSource,
            uuidgen=(types.FunctionType, uuid.UUID))
    def __init__(self, rt, ua, timesrc, uuidgen):
        '''
        Note sources of non-determinism (timesrc, uuidgen) are passed in as constructor args.
        .. todo:: collect notes on object-capability style and testability.
        '''
        self._token = rt.token
        self._api_url = rt.api_url
        self._ua = ua
        self._timesrc = timesrc
        self._uuidgen = uuidgen

    def add_record(self, user_id, disclaimer_address):
        # Rather than keeping track of the next record ID, we just use random IDs.
        ack = self._uuidgen()
        # YYYY-MM-DD hh:mm:ss
        timestamp = self._timesrc.now().isoformat(sep=' ')[:19]

        buf = StringIO.StringIO()
        rowbuf = csv.writer(buf)
        rowbuf.writerow(Acknowledgement.fields)
        record = (ack, timestamp, user_id, disclaimer_address)
        rowbuf.writerow(record)
        log.debug('adding record: %s' , record)

        args = {'token': self._token,
                'content': 'record',
                'type': 'flat',
                'format': 'csv',
                'data': buf.getvalue()}
        log.debug('posting %s to: %s', args, self._api_url)
        body = urllib.urlencode(args)
        self._ua.open(self._api_url, body)
        return record


class ModuleHelper(object):
    @classmethod
    def make_stuff(cls, ini, stuff=((sqlalchemy.engine.base.Connectable, redcapdb.CONFIG_SECTION),
                                    AcknowledgementsProject)):
        depgraph = injector.Injector(cls.mods(ini))
        return [depgraph.get(what) for what in stuff]


class Mock(redcapdb.SetUp, ModuleHelper, redcapdb.ModuleHelper):
    def __init__(self):
        sqlalchemy.orm.clear_mappers()

    @classmethod
    def mods(cls, ini=''):
        return redcapdb.Mock.mods(ini) + [cls(), TestSetUp()]

    @provides((config.Options, DISCLAIMERS_SECTION))
    def disclaimer_options(self):
        return config.TestTimeOptions(dict(project_id='123'))

    @provides((config.Options, ACKNOWLEGEMENTS_SECTION))
    def acknowledgements_options(self):
        return config.TestTimeOptions(dict(project_id='1234',
                                           api_url='http://example/recap/API',
                                           token='12345token'))
    @provides(urllib.URLopener)
    def web_ua(self):
        return _TestURLopener()

    @provides((types.FunctionType, uuid.UUID))
    def uuidgen_func(self):
        def _mock_uuidgen():
            return uuid.UUID('8bd21cf4-3e5f-4f09-9936-10301aa37b0a')
        return _mock_uuidgen

    @provides(KTimeSource)
    def time_source(self):
        return _TestTimeSource()


class TestSetUp(redcapdb.SetUp):
    @singleton
    @provides((sqlalchemy.orm.session.Session, redcapdb.CONFIG_SECTION))
    @inject(engine=(sqlalchemy.engine.base.Connectable, redcapdb.CONFIG_SECTION),
            drt=(config.Options, DISCLAIMERS_SECTION),
            art=(config.Options, ACKNOWLEGEMENTS_SECTION))
    def redcap_sessionmaker(self, engine, drt, art):
        smaker = super(TestSetUp, self).redcap_sessionmaker(engine=engine)
        Disclaimer.eav_map(drt.project_id)
        Acknowledgement.eav_map(art.project_id)
        s = smaker()
        insert_data = redcapdb.redcap_data.insert()
        for field_name, value in (
             ('disclaimer_id', '1'),
             ('url', 'http://example/blog/item/heron-release-xyz'),
             ('current', 1)):
            s.execute(insert_data.values(event_id=1,
                                         project_id=drt.project_id, record=1,
                                         field_name=field_name, value=value))

            log.debug('inserted: %s, %s', field_name, value)
        s.commit()

        return smaker


class _TestTimeSource(object):
    def now(self):
        return datetime.datetime(2011, 9, 2)

    def today(self):
        return datetime.date(2011, 9, 2)


class _TestURLopener(object):
    def open(self, addr, data=None):
        if addr.startswith('http://example/recap/API'):
            # todo: verify contents?
            return StringIO.StringIO('')
        else:
            raise IOError, '404 not found'


class RunTime(injector.Module, ModuleHelper):
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
        Disclaimer.eav_map(drt.project_id)

        art = bind_options('project_id api_url token'.split(),
                           ACKNOWLEGEMENTS_SECTION)
        Acknowledgement.eav_map(art.project_id)

        # function returning uuid.UUID
        binder.bind((types.FunctionType, uuid.UUID),
                    injector.InstanceProvider(uuid.uuid4))
        binder.bind(KTimeSource, injector.InstanceProvider(datetime.datetime))
        binder.bind(urllib.URLopener, urllib2.build_opener)


    @classmethod
    def mods(cls, ini):
        return redcapdb.RunTime.mods(ini) + [cls(ini)]


if __name__ == '__main__':
    import sys
    logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)

    engine, acks = RunTime.make_stuff('integration-test.ini')

    Base.metadata.bind = engine
    sm = sessionmaker(engine)

    if '--ack' in sys.argv:
        s = sm()
        user_id = sys.argv[2]
        d = s.query(Disclaimer).filter(Disclaimer.current==1).first()
        acks.add_record(user_id, d.url)

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
        c, h = d.content(urllib2.build_opener())
        print h
        print c[:100]
