'''checklist -- HERON repository access checklist
-------------------------------------------------

.. note:: This module remains for historical reasons;
   in retrospect, its functionality probably belongs
   in :mod:`heron_wsgi.admin_lib.heron_policy`
   and :class:`heron_wsgi.heron_srv.ChecklistView`.

For example, checklist for John Smith::

  >>> cl, hr, mc = Mock.make(
  ...    [Checklist, heron_policy.HeronRecords, medcenter.MedCenter])
  >>> roles = heron_policy.Mock.login_sim(mc, hr)

  >>> import pprint
  >>> pprint.pprint(cl.screen(*roles('john.smith')))
  {'accessDisabled': {'name': 'login'},
   'affiliate': John Smith <john.smith@js.example>,
   'executive': {},
   'faculty': {'checked': 'checked'},
   'signatureOnFile': {'checked': 'checked'},
   'sponsored': {'checked': 'checked'},
   'trainingCurrent': {'checked': 'checked'},
   'trainingExpiration': '2012-01-01'}

And Bill Student::

  >>> pprint.pprint(cl.screen(*roles('bill.student')))
  {'accessDisabled': {'disabled': 'disabled'},
   'affiliate': Bill Student <bill.student@js.example>,
   'executive': {},
   'faculty': {},
   'signatureOnFile': {},
   'sponsored': {},
   'trainingCurrent': {},
   'trainingExpiration': ''}

  >>> pprint.pprint(cl.screen(*roles('nobody')))
  Traceback (most recent call last):
    ...
  KeyError: 'nobody'


'''
import logging

import injector

import heron_policy
import medcenter
import rtconfig


log = logging.getLogger(__name__)


class Checklist(object):
    '''
    .. note:: There's no longer any reason for this to be a class.
    '''
    def __init__(self):
        pass

    def __repr__(self):
        return 'Checlist()'

    def screen(self, agent, faculty, executive):
        try:
            expiration = agent.training()
            current = {'checked': 'checked'}
        except heron_policy.NoTraining as e:
            expiration = e.when
            current = {}

        def checkmark(f):
            try:
                f()
                return {'checked': 'checked'}
            except heron_policy.NoPermission:
                return {}
            except medcenter.NotFaculty:
                return {}
            except IOError:
                log.warn('Exception in checklist. DB down?')
                log.debug('Checklist error detail', exc_info=True)
                # @@TODO: show user an indication of the error
                return {}

        try:
            access = agent.repository_authz()
        except heron_policy.NoPermission:
            access = None
        except IOError:
            log.warn('Exception checking repository access. DB down?')
            log.debug('Repository access error detail', exc_info=True)
            # @@TODO: show user an indication of the error
            access = None

        return {"affiliate": agent.badge,
                "trainingCurrent": current,
                "trainingExpiration": expiration,
                "executive": {'checked': 'checked'} if executive else {},
                "faculty": {'checked': 'checked'} if faculty else {},
                "signatureOnFile": checkmark(lambda: agent.signature()),
                "sponsored": checkmark(lambda: agent.sponsor()),
                "accessDisabled": (access and {'name': 'login'}
                                   or {'disabled': 'disabled'})}


class Mock(injector.Module, rtconfig.MockMixin):
    @classmethod
    def mods(cls):
        return [cls()] + heron_policy.Mock.mods()


class RunTime(rtconfig.IniModule):
    @classmethod
    def mods(cls, ini):
        return [cls(ini)] + heron_policy.RunTime.mods(ini)


if __name__ == '__main__':  # pragma nocover
    import sys
    uid = sys.argv[1]

    logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)

    mc, hr, check = RunTime.make(None, [medcenter.MedCenter,
                                        heron_policy.HeronRecords,
                                        Checklist])

    req = medcenter.Mock.login_info(uid)
    mc.issue(req)
    hr.issue(req)

    import pprint
    pprint.pprint(check.screen(req.user, req.faculty, req.executive))
