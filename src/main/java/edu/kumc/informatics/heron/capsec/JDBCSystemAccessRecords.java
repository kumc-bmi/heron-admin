/* Copyright (c) 2011 The University of Kansas Medical Center
 * http://informatics.kumc.edu/ */

package edu.kumc.informatics.heron.capsec;

import edu.kumc.informatics.heron.dao.HeronDBDao;
import java.security.acl.NotOwnerException;
import java.util.logging.Level;
import java.util.logging.Logger;
import javax.naming.NameNotFoundException;
import javax.naming.NoPermissionException;

/**
 *
 * @author dconnolly
 */
public class JDBCSystemAccessRecords implements SystemAccessRecords {
        private final AcademicMedicalCenter _org;
        private final DROCSponsoring _droc;
        private final HeronDBDao _heronData; // TODO: refactor

        private final IllegalArgumentException denied =
                new IllegalArgumentException("no system access records on file.");

	public JDBCSystemAccessRecords(AcademicMedicalCenter org, DROCSponsoring droc,
                HeronDBDao hd) {
		_org = org;
                _droc = droc;
                _heronData = hd;
	}

        /**
         * Turn a Ticket into a RepositoryUser, provided the ticket is from
         * a recognized agent who signed the system access agreement.
         * @param who
         * @return
         * @throws NoPermissionException
         */
        @Override
	public RepositoryUser asUser(Ticket who) throws NoPermissionException, NameNotFoundException {
                String username = who.getName();
                Agent asAgent = _org.affiliate(username);

                if (!_heronData.isUserAgreementSigned(username)) {
                        throw denied;
                }

                return new RepositoryUserImpl(asAgent, _org);
	}

        protected static class RepositoryUserImpl implements RepositoryUser {
                public RepositoryUserImpl(Agent who, AcademicMedicalCenter org){
                        _asAgent = who;
                        _org = org;                        
                }
                private final AcademicMedicalCenter _org;
                private final Agent _asAgent;
                
                @Override
                public String getMail() {
                        return _asAgent.getMail();
                }
                @Override
                public String getFullName() {
                        return _asAgent.getFullName();
                }
                @Override
                public String getTitle() {
                	    return _asAgent.getTitle();
                }
        }
        
        /**
         * Turn a Ticket into a Sponsor, provided the ticket is from
         * a qualified faculty member who signed the system access agreement.
         * @param who
         * @return
         * @throws NoPermissionException
         */
        @Override
	public Sponsor asSponsor(Ticket who) throws NoPermissionException {
		Agent who_a = _org.qualifiedFaculty(who);
                if (!_heronData.isUserAgreementSigned(who.getName())) {
                        throw denied;
                }

                return new SystemSponsor(who_a, _org, _droc);
	}

	protected static class SystemSponsor implements Sponsor {
		private AcademicMedicalCenter _org;
		private Agent _as_agent;
                private DROCSponsoring _droc;

		public SystemSponsor(Agent me, AcademicMedicalCenter org, DROCSponsoring d) {
			_org = org;
			_as_agent = me;
                        _droc = d;
		}

                @Override
		public void fileRequest(String title, Agent who) throws NotOwnerException {
			Agent who_a = _org.recognize(who);
                        _droc.postRequest(title, this, who);
		}
	}
}
