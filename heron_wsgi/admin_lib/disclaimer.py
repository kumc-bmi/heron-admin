'''disclaimer -- access disclaimers and acknowledgements from REDCap EAV DB
---------------------------------------------------------------------------

:class:`Disclaimer` and :class:`Acknowledgement` provide read-only
access via SQL queries.

:class:`AcknowledgementsProject`: supports adding records via the REDCap API.

Let's get a sessionmaker and an AcknowledgementsProject, which causes
the database to get set up::

  >>> smaker, acksproj = Mock.make((
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
  ... # doctest: +NORMALIZE_WHITESPACE
  [Disclaimer(disclaimer_id=1,
              url=http://example/blog/item/heron-release-xyz, current=1)]

'''

# python stdlib http://docs.python.org/library/
import StringIO
import logging
from xml.dom.minidom import parse

# from pypi
import injector
from injector import inject, provides, singleton
import sqlalchemy
from sqlalchemy.orm import sessionmaker
import xpath

# from this package
import rtconfig
import redcapdb
import redcap_connect

DISCLAIMERS_SECTION = 'disclaimers'
ACKNOWLEGEMENTS_SECTION = 'disclaimer_acknowledgements'
KTimeSource = injector.Key('TimeSource')

log = logging.getLogger(__name__)


class Disclaimer(redcapdb.REDCapRecord):
    fields = ('disclaimer_id', 'url', 'current')

    def content(self, ua):
        r'''
           >>> d = Disclaimer()
           >>> d.url = 'http://example/'
           >>> d.content(_MockTracBlog())
           ... # doctest: +ELLIPSIS
           (u'<div id="blog-main">\n<h1 class="blog-title">...', u'headline')
        '''
        body = ua.open(self.url).read()  # pylint: disable=E1101
        kludge = StringIO.StringIO(body.replace('&larr;', '').\
                                       replace('&rarr;', ''))  # KLUDGE
        elt = xpath.findnode('//*[@id="blog-main"]', parse(kludge))
        headline = xpath.findvalue('.//*[@class="blog-title"]/text()', elt)

        return elt.toxml(), headline

_test_doc = '''
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


class _MockTracBlog(object):
    def open(self, _):  # pylint: disable=R0201
        return StringIO.StringIO(_test_doc)


class Acknowledgement(redcapdb.REDCapRecord):
    fields = ('ack', 'timestamp', 'user_id', 'disclaimer_address')


class AcknowledgementsProject(object):
    '''AcknowledgementsProject serves as a REDCap API proxy for adding
    Acknowledgement records.
    '''
    @inject(proxy=(redcap_connect.EndPoint, ACKNOWLEGEMENTS_SECTION),
            timesrc=KTimeSource)
    def __init__(self, proxy, timesrc):
        self._proxy = proxy
        self._timesrc = timesrc

    def add_records(self, disclaimer_address, whowhen):
        # Rather than keeping track of the next record ID, we just use
        # random IDs.
        records = [dict(zip(Acknowledgement.fields,
                            # Pretty safe to assume last segments of
                            # disclaimer_addresses are distinct for
                            # all users acknowledging on a given day,
                            # especially since we choose addresses.
                            ('%s %s %s' % (timestamp.isoformat()[:10],
                                           uid, last_seg(disclaimer_address)),
                             # YYYY-MM-DD hh:mm:ss
                             timestamp.isoformat(sep=' ')[:19],
                             uid, disclaimer_address))
                        + [('acknowledgement_complete', '2')])
                   for uid, timestamp in whowhen]

        self._proxy.record_import(data=records)
        return records

    def add_record(self, user_id, disclaimer_address):
        timestamp = self._timesrc.now()

        return self.add_records(disclaimer_address,
                                [(user_id, timestamp)])[0]


def last_seg(addr):
    '''
    >>> last_seg('abc/def')
    '/def'
    '''
    return addr[addr.rfind('/'):]


class Mock(redcapdb.SetUp, rtconfig.MockMixin):
    def __init__(self):
        sqlalchemy.orm.clear_mappers()

    @classmethod
    def mods(cls):
        return redcapdb.Mock.mods() + [cls(), TestSetUp()]

    @provides((redcap_connect.EndPoint, ACKNOWLEGEMENTS_SECTION))
    def redcap_api_endpoint(self):
        webcap = redcap_connect._MockREDCapAPI()
        return redcap_connect.EndPoint(webcap, '12345token')

    @provides(KTimeSource)
    def time_source(self):
        return _TestTimeSource()


class TestSetUp(redcapdb.SetUp):
    disclaimer_pid = '123'
    ack_pid = '1234'

    @singleton
    @provides((sqlalchemy.orm.session.Session, redcapdb.CONFIG_SECTION))
    @inject(engine=(sqlalchemy.engine.base.Connectable,
                    redcapdb.CONFIG_SECTION))
    def redcap_sessionmaker(self, engine):
        smaker = super(TestSetUp, self).redcap_sessionmaker(engine=engine)
        Disclaimer.eav_map(self.disclaimer_pid)
        Acknowledgement.eav_map(self.ack_pid)
        s = smaker()
        insert_data = redcapdb.redcap_data.insert()
        for field_name, value in (
             ('disclaimer_id', '1'),
             ('url', 'http://example/blog/item/heron-release-xyz'),
             ('current', 1)):
            s.execute(insert_data.values(event_id=1,
                                         project_id=self.disclaimer_pid,
                                         record=1,
                                         field_name=field_name, value=value))

            log.debug('inserted: %s, %s', field_name, value)
        s.commit()

        return smaker


class _TestTimeSource(object):
    def now(self):
        import datetime
        return datetime.datetime(2011, 9, 2)

    def today(self):
        import datetime
        return datetime.date(2011, 9, 2)


class RunTime(rtconfig.IniModule):
    def configure(self, binder):
        drt = self.get_options(['project_id'], DISCLAIMERS_SECTION)
        Disclaimer.eav_map(drt.project_id)

        art, api = redcap_connect.RunTime.endpoint(
            self, ACKNOWLEGEMENTS_SECTION, extra=('project_id',))
        Acknowledgement.eav_map(art.project_id)

        binder.bind((redcap_connect.EndPoint, ACKNOWLEGEMENTS_SECTION),
                    injector.InstanceProvider(api))

    @provides(KTimeSource)
    def real_time(self):
        import datetime

        return datetime.datetime

    @classmethod
    def mods(cls, ini):
        return redcapdb.RunTime.mods(ini) + [cls(ini)]


def _test_main():
    import sys
    import urllib2

    logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)

    user_id = sys.argv[1]

    engine, acks = RunTime.make(None, [(sqlalchemy.engine.base.Connectable,
                                        redcapdb.CONFIG_SECTION),
                                       AcknowledgementsProject])
    redcapdb.Base.metadata.bind = engine
    sm = sessionmaker(engine)

    s = sm()
    d = s.query(Disclaimer).filter(Disclaimer.current == 1).first()
    log.info('current disclaimer: %s', d)
    a = s.query(Acknowledgement).\
        filter(Acknowledgement.disclaimer_address == d.url).\
        filter(Acknowledgement.user_id == user_id).first()
    log.info('ack for %s: %s', user_id, a)

    if '--ack' in sys.argv:
        d = s.query(Disclaimer).filter(Disclaimer.current == 1).first()
        acks.add_record(user_id, d.url)
        s.commit()

    if '--disclaimers' in sys.argv:
        print "all disclaimers:"
        for d in s.query(Disclaimer):
            print d

    if '--acks' in sys.argv:
        print 'all acknowledgements:'
        for ack in s.query(Acknowledgement):
            print ack

    if '--release-info' in sys.argv:
        from operator import attrgetter
        from itertools import groupby
        acks = s.query(Acknowledgement).all()
        per_release = dict([(addr, list(acks)) for addr, acks in
                             groupby(acks, attrgetter('disclaimer_address'))])
        users_per_release = dict([(addr, len(list(acks))) for addr, acks in
                                  per_release.iteritems()])
        start_release = dict([(addr, min([a.timestamp for a in acks]))
                              for addr, acks in
                              per_release.iteritems()])
        for release in per_release.keys():
            print "%s,%s,%s" % (start_release[release],
                                users_per_release[release], release)

    if '--current' in sys.argv:
        print "current disclaimer and content:"
        for d in s.query(Disclaimer).filter(Disclaimer.current == 1):
            print d
            c, h = d.content(urllib2.build_opener())
            print h
            print c[:100]


if __name__ == '__main__':
    _test_main()
