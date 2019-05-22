r'''drocnotice -- notify investigators, team members of DROC decisions
----------------------------------------------------------------------

  >>> from pyramid import testing
  >>> from pyramid.testing import DummyRequest
  >>> config = testing.setUp()

  >>> (dn, ) = Mock.make([DROCNotice])

  >>> config.add_route(DROCNotice.home, '')
  >>> config.add_route('notifier', '/notifier')
  >>> dn.configure(config, 'notifier')

  >>> for record, msg in dn.build_notices(DummyRequest()):
  ...     msg.sender = 'sender@example'  # kludge
  ...     m = msg.to_message()
  ...     print 'To:', m['to']
  ...     print 'Subject:', m['subject']
  ...     print 'Cc:', m['cc']
  To: john.smith@js.example
  Subject: HERON access request rejected
  Cc: None
  To: john.smith@js.example, bill.student@js.example
  Subject: HERON access request approved
  Cc: None
  To: john.smith@js.example, some.one@js.example, carol.student@js.example
  Subject: HERON access request approved
  Cc: None

Send the notices and log them in the DB:

  >>> ans = dn.send_notices(DummyRequest())
  >>> ans._app_iter # doctest: +NORMALIZE_WHITESPACE
  ['notice sent for record -565402122873664774:
    HERON access request rejected\n',
   'notice sent for record 23180811818680005:
    HERON access request approved\n',
   'notice sent for record 6373469799195807417:
   HERON access request approved\n']

Now there should be no pending notices:

  >>> list(dn.build_notices(DummyRequest()))
  []

'''

import logging

import injector
from injector import inject, provides
from pyramid.response import Response
from pyramid_mailer.mailer import Mailer, DummyMailer
from pyramid_mailer.message import Message
import sqlalchemy
from sqlalchemy.sql import func

import genshi_render
from admin_lib import heron_policy
from admin_lib.noticelog import DecisionRecords
from admin_lib import noticelog
from admin_lib import redcapdb
from admin_lib import rtconfig
from admin_lib.ocap_file import Token

KMailSettings = injector.Key('MailSettings')
log = logging.getLogger(__name__)


class DROCNotice(Token):
    # We send notice only on final decisions, not defer.
    FINAL_DECISIONS = (DecisionRecords.YES, DecisionRecords.NO)

    '''Route to HERON home page. '''
    home = 'heron_home'  # oops... should be passed in from heron_srv

    @inject(dr=DecisionRecords,
            smaker=(sqlalchemy.orm.session.Session, redcapdb.CONFIG_SECTION),
            mailer=Mailer)
    def __init__(self, dr, smaker, mailer):
        self._dr = dr
        self._rf = genshi_render.Factory({})
        self._smaker = smaker
        self._mailer = mailer

    def configure(self, config, route, permission=None):
        config.add_view(self.send_notices, route_name=route,
                        request_method='POST',
                        permission=permission)

    def send_notices(self, req):
        '''
        .. note:: The error handling strategy is: if anything goes wrong,
                  bail out and try again next time.

        '''
        mailer = self._mailer
        ins = noticelog.notice_log.insert()
        out = []

        for record, msg in self.build_notices(req):
            s = self._smaker()
            log.info('sending to: %s cc: %s', msg.recipients, msg.cc)
            mailer.send_immediately(msg)
            s.execute(ins.values(record=record, timestamp=func.now()))
            s.commit()
            notice = ('notice sent for record %s: %s\n' %
                      (str(record), str(msg.subject)))
            out.append(notice)
            log.info(notice)
        return Response(app_iter=out)

    def build_notices(self, req):
        dr = self._dr
        for record, decision, _ in dr.oversight_decisions():
            if decision not in self.FINAL_DECISIONS:
                continue

            action = ('approved' if decision == DecisionRecords.YES
                      else 'rejected')

            try:
                investigator, team, detail = dr.decision_detail(record)
                log.info('Notify %s and team that request %s is %s',
                         investigator, record, action)
            except Exception as oops:
                log.error('build_notices: bad record? %s: %s' % (record, oops))
                continue

            try:
                log.debug('build_notices team: %s', team)
                inv_mail, team_mail = dr.team_email(
                    investigator.cn,
                    [mem.cn for mem in team]
                    if decision == DecisionRecords.YES else [])
            except KeyError as ke:
                log.warn('notification re %s failed; cannot get team_email',
                         record, exc_info=ke)
                continue

            body = self._rf(render_value(investigator, team, decision, detail,
                                         req.route_path(self.home)),
                            dict(renderer_name='drocnotice.html'))

            m = Message(subject='HERON access request ' + action,
                        # Due to bug in pyramid_mailer, we don't use cc.
                        # https://github.com/Pylons/pyramid_mailer/issues/3
                        # https://github.com/dckc/pyramid_mailer/commit
                        #    /8a426bc8b24f491880c2b3a0204f0ee7bae42193
                        # cc=cc,
                        recipients=[inv_mail] + team_mail,
                        html=body)

            yield record, m


def render_value(investigator, team, decision, detail, heron_home):
    r'''
      >>> from admin_lib.noticelog import Ref
      >>> v = render_value(Ref('john.smith', 'John Smith', 'js...'),
      ...                  [Ref('some.one', 'Some One', 'so...')], '1',
      ...                  dict(full_name='John Smith',
      ...                       project_title='Study Warts',
      ...                       name_etc_1='Some One\netc.'),
      ...                  'http://example/heron/')
      >>> from pprint import pprint
      >>> pprint(v)
      {'approved': True,
       'full_name': 'John Smith',
       'heron_home': 'http://example/heron/',
       'name_etc_1': 'Some One\netc.',
       'project_title': 'Study Warts',
       'sponsor_full_name': 'John Smith',
       'team': ['Some One']}

    Check that this supplies everything the template expects::
      >>> f = genshi_render.Factory({})
      >>> s = f(v, dict(renderer_name='drocnotice.html'))
      >>> 'Study Warts' in s
      True
    '''
    return dict(detail,
                heron_home=heron_home,
                approved=decision == DecisionRecords.YES,
                sponsor_full_name=investigator.full_name(),
                team=[mem.full_name() for mem in team])


class Mock(injector.Module, rtconfig.MockMixin):
    stuff = [DROCNotice]

    @provides(KMailSettings)
    def settings(self):
        return {}

    @provides(Mailer)
    def mailer(self):
        return DummyMailer()

    @classmethod
    def mods(cls):
        return [cls()] + heron_policy.Mock.mods()
