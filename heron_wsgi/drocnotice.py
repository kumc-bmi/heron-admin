r'''drocnotice -- notify investigators, team members of DROC decisions

  >>> from pyramid import testing
  >>> from pyramid.testing import DummyRequest
  >>> config = testing.setUp()
  >>> config.add_route('heron_home', '')
  >>> dn = Mock.make()
  >>> dn.configure(config, 'heron_home')
  >>> for record, msg in dn.build_notices(DummyRequest()):
  ...     msg.to_message()['Subject']
  'HERON access request approved'

  Send the notices and log them in the DB:
  >>> dn.send_notices(DummyRequest())

  Now there should be no pending notices:
  >>> list(dn.build_notices(DummyRequest()))
  []

'''

import injector
from injector import inject
from pyramid_mailer import get_mailer
from pyramid_mailer.message import Message
import sqlalchemy
from sqlalchemy.sql import func

import genshi_render
from admin_lib import heron_policy
from admin_lib import medcenter
from admin_lib import noticelog
from admin_lib import redcapdb

class DROCNotice(object):
    '''
    .. todo:: factor out heron-admin address
    '''
    @inject(dr=heron_policy.DecisionRecords,
            smaker=(sqlalchemy.orm.session.Session, redcapdb.CONFIG_SECTION))
    def __init__(self, dr, smaker, sender='heron-admin@kumc.edu'):
        self._dr = dr
        self._rf = genshi_render.Factory({})
        self._sender = sender
        self._smaker = smaker

    def configure(self, config, route):
        config.include('pyramid_mailer')
        config.add_view(self.send_notices, route_name=route,
                        request_method='POST')

    def send_notices(self, req):
        '''
        .. note:: The error handling strategy is: if anything goes wrong,
                  bail out and try again next time.
        '''
        mailer = get_mailer(req)
        ins = noticelog.notice_log.insert()
        for record, msg in self.build_notices(req):
            s = self._smaker()
            mailer.send(msg)
            s.execute(ins.values(record=record, timestamp=func.now()))
            s.commit()

    def build_notices(self, req):
        dr = self._dr
        for pid, record, decision, _ in dr.oversight_decisions():
            if decision not in ('1', '2'):
                continue  # e.g. deferred

            investigator, team, detail = dr.decision_detail(record)
            s = self._rf(render_value(investigator, team, decision, detail,
                              req.route_url('heron_home')),
                         dict(renderer_name='drocnotice.html'))

            m = Message(subject=('HERON access request ' +
                                 'approved' if decision == '1' else 'rejected'),
                        sender=self._sender,
                        recipients=[investigator.mail],
                        cc = ([b.mail for b in team] if decision == '1'
                              else []),
                        html=s)

            yield record, m


def render_value(investigator, team, decision, detail, heron_home):
    r'''
      >>> mc = medcenter.Mock.make()
      >>> v = render_value(mc.lookup('john.smith'),
      ...                  [mc.lookup('some.one')], '1',
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

      >>> f = genshi_render.Factory({})
      >>> s = f(v, dict(renderer_name='drocnotice.html'))
      >>> 'Some One' in s
      True
    '''
    return dict(detail,
                heron_home=heron_home,
                approved=decision=='1',
                sponsor_full_name=detail['full_name'],
                team=['%s %s' % (b.givenname, b.sn) for b in team])


class Mock(injector.Module):
    @classmethod
    def make(cls):
        depgraph = injector.Injector(heron_policy.Mock.mods())
        return depgraph.get(DROCNotice)

    
