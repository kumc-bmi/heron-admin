import datetime


def checklist(medcenter, uid, timesrc):
    try:
        expiration = medcenter.trainedThru(uid)
        expired = expiration >= timesrc.today().isoformat()
    except KeyError:
        expired = True

    

    return {"affiliate": medcenter.affiliate(uid),
            "trainingExpired": expired,
            "trainingExpiration": expiration,
        	EXECUTIVE("executive"),
        	FACULTY("faculty"),
        	SPONSORED("sponsored"), // TODO: think of a better name
        	SPONSOR("sponsor"),
        	SIGNATURE_ON_FILE("signatureOnFile"),
        	REPOSITORY_USER("repositoryUser"),
        	REPOSITORY_TOOL("repositoryTool"),
        	SPONSORSHIP_FORM("sponsorshipForm");
