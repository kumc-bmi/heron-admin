/* Copyright (c) 2011 The University of Kansas Medical Center
 * http://informatics.kumc.edu/ */

package edu.kumc.informatics.heron.capsec;

import edu.kumc.informatics.heron.dao.HeronDBDao;
import edu.kumc.informatics.heron.dao.HeronDao;
import edu.kumc.informatics.heron.util.Functional.Function1;

import java.util.Date;

import javax.naming.NoPermissionException;
import javax.servlet.ServletException;
import javax.servlet.http.HttpServletRequest;

/**
 *
 * @author dconnolly
 */
public class JDBCSystemAccessRecords implements SystemAccessRecords {
        private final AcademicMedicalCenter _org;
        private final DROCSponsoring _droc;
        private final HeronDao _heronData; // TODO: abstract interface

	public JDBCSystemAccessRecords(AcademicMedicalCenter org, DROCSponsoring droc,
                HeronDao hd) {
		_org = org;
                _droc = droc;
                _heronData = hd;
	}

	private class Qualified implements Qualification {
		Qualified(Agent who) {
			_who = who;
		}
		private final Agent _who;
		public Agent forWhom() {
			return _who;
		}
	}
	
	@Override
	public Qualification executiveUser(HttpServletRequest q) throws NoPermissionException, ServletException {
		Agent who = _org.affiliate(q);
	        if (!_heronData.isUserExecutive(who)) {
	                throw notExecutive;
	        }

	        return new Qualified(who);
	}

	public RepositoryUser repositoryUser(Agent who, Qualification q) throws NoPermissionException {
		if (q.forWhom() != who) {
			throw new IllegalArgumentException("bad qualification for:" + who); // todo: Agent.toString()
		}
	        Date training_expires = _org.trainedThru(who);

	        if (_heronData.expired(training_expires)) {
                	throw trainingOutOfDate;
                }

                if (!_heronData.isUserAgreementSigned(who)) {
                        throw nosig;
                }

	        return new RepositoryUserImpl(who, training_expires, _heronData.disclaimer(who));
	}
	

	private static final Function1<Agent, Agent> identity = new Function1<Agent, Agent>() {
		@Override
		public Agent apply(Agent who) {
			return who;
		}
	};

	@Override
	public Qualification facultyUser(HttpServletRequest q)
	                throws NoPermissionException, ServletException {
		Agent a = _org.affiliate(q);

		// throw NoPermission unless a is faculty
		_org.withFaculty(a, identity);

	        return new Qualified(a);
	}

	@Override
	public Qualification sponsoredUser(HttpServletRequest q) throws NoPermissionException, ServletException {
		Agent a = _org.affiliate(q);
		if (!_heronData.isViewOnlyUserApproved(a)) {
			throw notSponsored;
		}
	        return new Qualified(a);
	}
	
	@Override
	public Qualification qualifiedUser(HttpServletRequest q) throws NoPermissionException, ServletException {
		try {
			return executiveUser(q);
		} catch (NoPermissionException notexec) {
			try {
				return facultyUser(q);
			} catch (NoPermissionException notfac) {
				return sponsoredUser(q);
			}
		}
	}

        protected static class RepositoryUserImpl implements RepositoryUser {
                public RepositoryUserImpl(Agent who, Date exp, HeronDBDao.Disclaimer d){
                        _asAgent = who;
                        _disclaimer = d;
                        _exp = exp;
                }
                private final Agent _asAgent;
                private final HeronDBDao.Disclaimer _disclaimer;
                private Date _exp;
                
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
                @Override
                public String getUserId() {
                        return _asAgent.getUserId();
                }
                @Override
                public Date getHSCTrainingExpiration() {
                        return _exp;
                }
                @Override
                public boolean acknowledgedRecentDisclaimers() {
                        return _disclaimer.wasRead();
                }
                @Override
                public void acknowledgeRecentDisclaimers() {
                        _disclaimer.recordAckowledgement();
                }
        }
        
        /**
         * Turn a request into a Sponsor, provided the request is from
         * a qualified faculty member who signed the system access agreement.
         * @param who
         * @return
         * @throws NoPermissionException
         * @throws ServletException 
         */
        @Override
	public Sponsor asSponsor(HttpServletRequest q) throws NoPermissionException, ServletException {
        	Agent a = _org.affiliate(q);
        	_org.withFaculty(a, identity);
                if (!_heronData.isUserAgreementSigned(a)) {
                        throw nosig;
                }
        	return new SystemSponsor(a, _droc); // TODO: facet of _droc?
	}

	protected static class SystemSponsor implements Sponsor {
                private DROCSponsoring _droc; // TODO: wrong class?

		public SystemSponsor(Agent me, DROCSponsoring d) {
                        _droc = d;
		}

                @Override
		public void fileRequest(String title, Agent who) {
                	throw new RuntimeException("fileRequest not yet implemented"); //TODO
		}
	}
}
