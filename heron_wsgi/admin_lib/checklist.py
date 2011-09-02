'''

  >>> import pprint
  >>> cl = _doctester()
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

import heron_policy
import medcenter

class Checklist(object):
    def __init__(self, medcenter, heron_records, timesrc):
        self._m = medcenter
        self._hr = heron_records
        self._t = timesrc

    def access_for(self, uid):
        agt = self._m.affiliate(uid)
        q = self._hr.q_any(agt)
        return self._hr.repositoryAccess(q)

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


def _doctester():
    import medcenter
    import heron_policy
    m = medcenter._doctester()
    hr = heron_policy._doctester()
    return Checklist(m, hr, heron_policy._TestTimeSource())


def _integration_test():
    import datetime
    import medcenter
    import heron_policy
    m = medcenter._integration_test()
    hr = heron_policy._integration_test()
    return Checklist(m, hr, datetime.date)


if __name__ == '__main__':
    import sys
    uid = sys.argv[1]

    check = _integration_test()

    import pprint
    pprint.pprint(check.parts_for(uid))
