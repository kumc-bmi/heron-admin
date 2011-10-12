'''


  >>> cl, hr, mc, depgraph = Mock.make_stuff()
  >>> role = heron_policy.Mock.login_sim(mc, hr)

  >>> import pprint
  >>> pprint.pprint(cl.screen(role('john.smith')))
  {'accessDisabled': {'name': 'login'},
   'affiliate': John Smith <john.smith@js.example>,
   'executive': {},
   'faculty': {'checked': 'checked'},
   'signatureOnFile': {'checked': 'checked'},
   'sponsored': {'checked': 'checked'},
   'trainingCurrent': {'checked': 'checked'},
   'trainingExpiration': '2012-01-01'}

  >>> pprint.pprint(cl.screen(role('bill.student')))
  {'accessDisabled': {'disabled': 'disabled'},
   'affiliate': Bill Student <bill.student@js.example>,
   'executive': {},
   'faculty': {},
   'signatureOnFile': {},
   'sponsored': {},
   'trainingCurrent': {},
   'trainingExpiration': ''}

  >>> pprint.pprint(cl.screen(role('nobody')))
  Traceback (most recent call last):
    ...
  KeyError: 'nobody'


'''

import injector
from injector import inject

import heron_policy
import medcenter

class Checklist(object):
    @inject(timesrc=heron_policy.KTimeSource)
    def __init__(self, timesrc):
        self._t = timesrc

    def __repr__(self):
        return 'Checlist(m, hr, t)'

    def screen(self, agent):
        try:
            expiration = agent.training()
            current = (expiration >= self._t.today().isoformat()
                       and {'checked': 'checked'} or {})
        except KeyError:
            expiration = None
            current = {}

        def checkmark(f):
            try:
                f()
                return {'checked': 'checked'}
            except heron_policy.NoPermission:
                return {}
            except medcenter.NotFaculty:
                return {}

        try:
            access = agent.repository_account()
        except heron_policy.NoPermission:
            access = None

        return {"affiliate": agent.badge,
                "trainingCurrent": current,
                "trainingExpiration": expiration,
                "executive": {},  #@@todo
                "faculty": checkmark(lambda: agent.faculty_title()),
                "signatureOnFile": checkmark(lambda: agent.signature()),
                "sponsored": checkmark(lambda: agent.sponsor()),
                "accessDisabled": (access and {'name': 'login'}
                                   or {'disabled': 'disabled'})
                }


class Mock(injector.Module):
    def configure(self, binder):
        pass

    @classmethod
    def mods(cls):
        return [cls()] + heron_policy.Mock.mods()

    @classmethod
    def make_stuff(cls):
        mc, hr, depgraph = heron_policy.Mock.make_stuff(cls.mods())
        cl = depgraph.get(Checklist)
        return cl, hr, mc, depgraph


class IntegrationTest(injector.Module):
    def configure(self, binder):
        pass

    @classmethod
    def deps(cls):
        return [cls] + heron_policy.IntegrationTest.deps()

    @classmethod
    def depgraph(cls):
        return injector.Injector([class_() for class_ in cls.deps()])


if __name__ == '__main__':  # pragma nocover
    import sys
    uid = sys.argv[1]

    depgraph = IntegrationTest.depgraph()
    check = depgraph.get(Checklist)

    import pprint
    pprint.pprint(check.parts_for(uid))
