import heron_policy
import medcenter

class Checklist(object):
    def __init__(self, medcenter, heron_records, timesrc):
        self._m = medcenter
        self._hr = heron_records
        self._t = timesrc

    def parts_for(self, uid):
        agt = self._m.affiliate(uid)

        try:
            expiration = self._m.trainedThru(agt)
            expired = expiration < self._t.today().isoformat()
        except KeyError:
            expiration = None
            expired = True

        def check_perm(f):
            try:
                f(agt)
                return True
            except heron_policy.NoPermission:
                return False
            except medcenter.NotFaculty:
                return False

        try:
            q = self._hr.q_any(agt)
            access = self._hr.repositoryAccess(q)
        except heron_policy.NoPermission:
            access = None

        return {"affiliate": agt,
                "trainingExpired": expired,
                "trainingExpiration": expiration,
                "executive": check_perm(self._hr.q_executive),
                "faculty": check_perm(self._m.checkFaculty),
                "signatureOnFile": self._hr.saa_signed(agt),
                "sponsored": check_perm(self._hr.q_sponsored),
                "repositoryUser": access
                #SPONSOR("as_sponsor"),
                #REPOSITORY_TOOL("repositoryTool"),
                #SPONSORSHIP_FORM("sponsorshipForm");
                }


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
