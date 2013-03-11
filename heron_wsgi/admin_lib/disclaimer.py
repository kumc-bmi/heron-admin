r'''disclaimer -- access disclaimers and acknowledgements from REDCap EAV DB
---------------------------------------------------------------------------

  >>> logging.basicConfig(level=logging.INFO)
  ... logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

A DisclaimerGuard provides a power only to those who have acknowledged
a disclaimer:

  >>> dg, notary = Mock.make((DisclaimerGuard, KNotary))
  >>> dg
  DisclaimerGuard()
  >>> notary
  Notary(disclaimer)
  >>> notary.getInspector()
  Inspector(disclaimer)

You can't acknowledge a disclaimer without a notarized badge:

  >>> import medcenter
  >>> x = medcenter.Badge(cn='john.smith',
  ...                     givenname='John', sn='Smith')
  >>> dg.ack_disclaimer(x)
  Traceback (most recent call last):
    ...
  NotVouchable

  >>> who = medcenter.IDBadge(notary, cn='john.smith',
  ...                         givenname='John', sn='Smith',
  ...                         mail='john.smith@js.example')
  >>> who
  John Smith <john.smith@js.example>
  >>> notary.getInspector().vouch(who)
  John Smith <john.smith@js.example>

  >>> def use_i2b2(badge):
  ...     return '%s authorized to use i2b2' % badge.cn
  >>> redeem = dg.make_redeem(use_i2b2)

Smith can't redeem his acknowledgement yet because he hasn't done one::

  >>> redeem(who)
  Traceback (most recent call last):
    ...
  KeyError: 'john.smith'

  >>> dg.ack_disclaimer(who)
  >>> redeem(who)
  'john.smith authorized to use i2b2'

Database Access
---------------

:class:`Disclaimer` and :class:`Acknowledgement` provide read-only
access via SQL queries.

:class:`AcknowledgementsProject`: supports adding records via the REDCap API.

Let's get a sessionmaker and an AcknowledgementsProject, which causes
the database to get set up::

  >>> smaker, acksproj, blog = Mock.make((
  ...       (sqlalchemy.orm.session.Session, redcapdb.CONFIG_SECTION),
  ...        AcknowledgementsProject, (WebReadable, DISCLAIMERS_SECTION)))
  >>> s = smaker()
  >>> for row in s.execute(redcapdb.redcap_data.select().where(
  ...  redcapdb.redcap_data.c.project_id == Mock.disclaimer_pid)).fetchall():
  ...     print row
  (123, 1, u'1', u'current', u'1')
  (123, 1, u'1', u'disclaimer_id', u'1')
  (123, 1, u'1', u'url', u'http://example/blog/item/heron-release-xyz')

Now note the mapping to the Disclaimer class::

  >>> dall = s.query(Disclaimer).all()
  >>> dall # doctest: +NORMALIZE_WHITESPACE
  [Disclaimer(disclaimer_id=1,
              url=http://example/blog/item/heron-release-xyz, current=1)]
  >>> dall[0].content(blog)[0][:30]
  u'<div id="blog-main">\n<h1 class'

  .>> acksproj.add_record('bob', 'http://informatics.kumc.edu/blog/2012/x')
  .>> for ack in s.query(Acknowledgement):
  ...     print ack
  '@@'

'''

# python stdlib http://docs.python.org/library/
import json
import StringIO
import logging
from xml.dom.minidom import parse

# from pypi
import injector
from injector import inject, provides, singleton
import sqlalchemy
from sqlalchemy.orm import session, sessionmaker, exc
import xpath

# from this package
from ocap_file import WebReadable, Token
import rtconfig
import redcapdb
import redcap_connect

DISCLAIMERS_SECTION = 'disclaimers'
ACKNOWLEGEMENTS_SECTION = 'disclaimer_acknowledgements'

KTimeSource = injector.Key('TimeSource')
KNotary = injector.Key('Notary')
KBadgeInspector = injector.Key('BadgeInspector')

log = logging.getLogger(__name__)


class Disclaimer(redcapdb.REDCapRecord):
    fields = ('disclaimer_id', 'url', 'current')

    def content(self, rdcap):
        r'''
           >>> d = Disclaimer()
           >>> d.url = 'http://example/'
           >>> d.content(_MockTracBlog())
           ... # doctest: +ELLIPSIS
           (u'<div id="blog-main">\n<h1 class="blog-title">...', u'headline')
        '''
        body = rdcap.subRdFile(self.url).getBytes()
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
    def inChannel(self):
        return StringIO.StringIO(_test_doc)

    def getBytes(self):
        return self.inChannel().read()

    def subRdFile(self, path):
        return self


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


class DisclaimerGuard(Token):
    @inject(smaker=(session.Session,
                    redcapdb.CONFIG_SECTION),
            badge_inspector=KBadgeInspector,
            acks=AcknowledgementsProject)
    def __init__(self, smaker, acks, badge_inspector):
        self.__smaker = smaker
        self.__badge_inspector = badge_inspector
        self.__acks = acks

    def __repr__(self):
        return '%s()' % self.__class__.__name__

    def current_disclaimer(self):
        s = self.__smaker()
        return s.query(Disclaimer).filter(Disclaimer.current == 1).one()

    def ack_disclaimer(self, alleged_badge):
        '''
        TODO: split object between read-only and read/write
        '''
        badge = self.__badge_inspector.vouch(alleged_badge)

        d = self.current_disclaimer()
        self.__acks.add_record(badge.cn, d.url)

    def make_redeem(self, guarded_power):
        def redeem(alleged_badge):
            badge = self.__badge_inspector.vouch(alleged_badge)

            s = self.__smaker()
            d = self.current_disclaimer()
            log.debug('disclaimer: %s', d)
            log.debug('first 10 acks: %s',
                      s.query(Acknowledgement)[:10])

            try:
                a = s.query(Acknowledgement).\
                    filter(Acknowledgement.disclaimer_address == d.url).\
                    filter(Acknowledgement.user_id == badge.cn).one()
            except exc.NoResultFound:
                raise KeyError(badge.cn)

                log.info('disclaimer ack: %s', a)

            return guarded_power(badge)

        return redeem


class _MockREDCapAPI2(redcap_connect._MockREDCapAPI):
    project_id = redcap_connect._test_settings.project_id

    def __init__(self, smaker):
        self.__smaker = smaker

    def dispatch(self, params):
        if 'import' in params['action']:
            return self.service_import(params)
        else:
            return super(_MockREDCapAPI2, self).dispatch(params)

    def service_import(self, params):
        from redcapdb import add_test_eav

        rows = json.loads(params['data'][0])
        schema = rows[0].keys()
        if sorted(schema) == sorted([u'ack', u'timestamp',
                                     u'disclaimer_address',
                                     u'user_id', u'acknowledgement_complete']):
            values = rows[0]
            record = hash(values['user_id'])
            s = self.__smaker()
            add_test_eav(s, self.project_id, 1,
                         record, values.items())
            return StringIO.StringIO('')
        else:
            raise IOError('bad request: bad acknowledgement schema: '
                          + str(schema))


class Mock(redcapdb.SetUp, rtconfig.MockMixin):
    disclaimer_pid = '123'
    ack_pid = redcap_connect._test_settings.project_id

    def __init__(self):
        from notary import makeNotary
        sqlalchemy.orm.clear_mappers()
        self._notary = makeNotary(__name__)

        Disclaimer.eav_map(self.disclaimer_pid)
        Acknowledgement.eav_map(self.ack_pid)

    @classmethod
    def mods(cls):
        return redcapdb.Mock.mods() + [cls()]

    @provides((WebReadable, DISCLAIMERS_SECTION))
    def rdblog(self):
        return _MockTracBlog()

    @provides((redcap_connect.EndPoint, ACKNOWLEGEMENTS_SECTION))
    @inject(smaker=(sqlalchemy.orm.session.Session, redcapdb.CONFIG_SECTION))
    def redcap_api_endpoint(self, smaker):
        webcap = _MockREDCapAPI2(smaker)
        return redcap_connect.EndPoint(webcap, '12345token')

    @provides(KTimeSource)
    def time_source(self):
        return _TestTimeSource()

    @provides(KBadgeInspector)
    def badge_inspector(self):
        return self._notary.getInspector()

    @provides(KNotary)
    def notary(self):
        return self._notary


class TestSetUp(redcapdb.SetUp):

    @singleton
    @provides((sqlalchemy.orm.session.Session, redcapdb.CONFIG_SECTION))
    @inject(engine=(sqlalchemy.engine.base.Connectable,
                    redcapdb.CONFIG_SECTION))
    def redcap_sessionmaker(self, engine):
        smaker = super(TestSetUp, self).redcap_sessionmaker(engine=engine)
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


class RunTime(rtconfig.IniModule):  # pragma: nocover
    def configure(self, binder):
        drt = self.get_options(['project_id'], DISCLAIMERS_SECTION)
        Disclaimer.eav_map(drt.project_id)

        art, api = redcap_connect.RunTime.endpoint(
            self, ACKNOWLEGEMENTS_SECTION, extra=('project_id',))
        Acknowledgement.eav_map(art.project_id)

        binder.bind((redcap_connect.EndPoint, ACKNOWLEGEMENTS_SECTION),
                    injector.InstanceProvider(api))

    @provides((WebReadable, DISCLAIMERS_SECTION))
    def rdblog(self, site='http://informatics.kumc.edu/'):
        from urllib2 import build_opener, Request
        return WebReadable(site, build_opener(), Request)

    @provides(KTimeSource)
    def real_time(self):
        import datetime

        return datetime.datetime

    @classmethod
    def mods(cls, ini):
        return redcapdb.RunTime.mods(ini) + [cls(ini)]


def _integration_test():  # pragma: nocover
    import sys

    logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)

    user_id = sys.argv[1]

    engine, acks, webrd = RunTime.make(None,
                                       [(sqlalchemy.engine.base.Connectable,
                                         redcapdb.CONFIG_SECTION),
                                        AcknowledgementsProject,
                                        (WebReadable, DISCLAIMERS_SECTION)])
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
        for start, count, url in _release_info(s):
            print "%s,%s,%s" % (start, count, url)

    if '--current' in sys.argv:
        print "current disclaimer and content:"
        for d in s.query(Disclaimer).filter(Disclaimer.current == 1):
            print d
            c, h = d.content(webrd)
            print h
            print c[:100]


def _release_info(s):
    '''Look for 1st ack for each release
    '''
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
    return [(start_release[release],
             users_per_release[release], release)
            for release in sorted(per_release.keys(),
                                  key=lambda r: start_release[r])]

if __name__ == '__main__':  # pragma: nocover
    _integration_test()
