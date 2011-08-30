

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
            expired = True

        return {"affiliate": agt,
                "trainingExpired": expired,
                "trainingExpiration": expiration,
                "executive": self._hr.is_executive(agt),
                "faculty": self._m.qualifiedFaculty(agt),
                #SIGNATURE_ON_FILE("signatureOnFile"),
                #"sponsored"), // TODO: think of a better name
                #SPONSOR("as_sponsor"),
                #REPOSITORY_USER("repositoryUser"),
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

    print check.parts_for(uid)
