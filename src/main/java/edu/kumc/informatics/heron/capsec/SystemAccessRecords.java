/* Copyright (c) 2011 The University of Kansas Medical Center
 * http://informatics.kumc.edu/ */

package edu.kumc.informatics.heron.capsec;

import edu.kumc.informatics.heron.dao.HeronDBDao;

/**
 *
 * @author dconnolly
 */
public class SystemAccessRecords {
        private final Enterprise _org;
        private final DROCSponsoring _droc;
        private final HeronDBDao _heronData; // TODO: refactor

        private final IllegalArgumentException denied =
                new IllegalArgumentException("no system access records on file.");

	public SystemAccessRecords(Enterprise org, DROCSponsoring droc,
                HeronDBDao hd) {
		_org = org;
                _droc = droc;
                _heronData = hd;
	}

        /**
         * Turn a Ticket into a Sponsor, provided the ticket is from
         * a qualified faculty member who signed the system access agreement.
         * @param who
         * @return
         */
	public Sponsor asSponsor(Ticket who) {
		Agent who_a = _org.qualifiedFaculty(who);
                if (!_heronData.isUserAgreementSigned(who.getName())) {
                        throw denied;
                }

                return new SystemSponsor(who_a, _org, _droc);
	}

	protected static class SystemSponsor implements Sponsor {
		private Enterprise _org;
		private Agent _as_agent;
                private DROCSponsoring _droc;

		public SystemSponsor(Agent me, Enterprise org, DROCSponsoring d) {
			_org = org;
			_as_agent = me;
                        _droc = d;
		}

                @Override
		public void fileRequest(String title, Agent who) {
			Agent who_a = _org.recognize(who);
                        _droc.postRequest(title, this, who);
		}
	}
}
