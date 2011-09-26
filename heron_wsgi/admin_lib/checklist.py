'''


  >>> depgraph = injector.Injector([Mock(),
  ...                               heron_policy.Mock(), medcenter.Mock()])
  >>> m = depgraph.get(medcenter.MedCenter)
  >>> hr = depgraph.get(heron_policy.HeronRecords)
  >>> cl = depgraph.get(Checklist)

  >>> import pprint
  >>> pprint.pprint(cl.parts_for('john.smith'))
  {'accessDisabled': {'name': 'login'},
   'affiliate': John Smith <john.smith@js.example>,
   'executive': {},
   'faculty': {'checked': 'checked'},
   'signatureOnFile': {'checked': 'checked'},
   'sponsored': {},
   'trainingCurrent': {'checked': 'checked'},
   'trainingExpiration': '2012-01-01'}

  >>> pprint.pprint(cl.parts_for('bill.student'))
  {'accessDisabled': {'disabled': 'disabled'},
   'affiliate': Bill Student <bill.student@js.example>,
   'executive': {},
   'faculty': {},
   'signatureOnFile': {},
   'sponsored': {},
   'trainingCurrent': {},
   'trainingExpiration': ''}

  >>> pprint.pprint(cl.parts_for('nobody'))
  Traceback (most recent call last):
    ...
  KeyError: 'nobody'


'''

import injector
from injector import inject

import heron_policy
import medcenter

class Checklist(object):
    @inject(mc=medcenter.MedCenter,
            heron_records=heron_policy.HeronRecords,
            timesrc=heron_policy.KTimeSource)
    def __init__(self, mc, heron_records, timesrc):
        self._m = mc
        self._hr = heron_records
        self._t = timesrc

    def __repr__(self):
        return 'Checlist(m, hr, t)'

    def medcenter(self):
        return self._m

    def heron_records(self):
        return self._hr

    def parts_for(self, uid):
        agt = self._m.affiliate(uid)

        try:
            expiration = self._m.trainedThru(agt)
            current = (expiration >= self._t.today().isoformat()
                       and {'checked': 'checked'} or {})
        except KeyError:
            expiration = None
            current = {}

        def check_perm(f):
            try:
                f(agt)
                return {'checked': 'checked'}
            except heron_policy.NoPermission:
                return {}
            except medcenter.NotFaculty:
                return {}

        try:
            q = self._hr.q_any(agt)
            access = self._hr.repositoryAccess(q)
        except heron_policy.NoPermission:
            access = None

        return {"affiliate": agt,
                "trainingCurrent": current,
                "trainingExpiration": expiration,
                "executive": check_perm(self._hr.q_executive),
                "faculty": check_perm(self._m.checkFaculty),
                "signatureOnFile": check_perm(self._hr.check_saa_signed),
                "sponsored": check_perm(self._hr.q_sponsored),
                "accessDisabled": (access and {'name': 'login'}
                                   or {'disabled': 'disabled'})
                #SPONSOR("as_sponsor"),
                #REPOSITORY_TOOL("repositoryTool"),
                #SPONSORSHIP_FORM("sponsorshipForm");
                }


class Mock(injector.Module):
    def configure(self, binder):
        pass


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
