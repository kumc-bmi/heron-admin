package edu.kumc.informatics.heron.dao;

import java.util.Date;
import java.util.List;

import org.springframework.dao.DataAccessException;

import edu.kumc.informatics.heron.capsec.Agent;
import edu.kumc.informatics.heron.dao.HeronDBDao.Disclaimer;
import edu.kumc.informatics.heron.util.Functional.Pair;

public interface HeronDao {

	/**
	 * check if user has signed system access agreement.
	 * 
	 * @param userId
	 * @return true if yes, false otherwise
	 * @throws DataAccessException
	 */
	public abstract boolean isUserAgreementSigned(Agent user)
	                throws DataAccessException;

	/**
	 * check if a view_only user is sponsored and approved.
	 * 
	 * @param uid
	 * @return true if sponsored and approved.
	 */
	public abstract boolean isViewOnlyUserApproved(Agent who);

	/**
	 * check if user an executive
	 * 
	 * @param uid
	 * @return true if yes
	 */
	public abstract boolean isUserExecutive(Agent who);

	public abstract Disclaimer disclaimer(final Agent who);

	/**
	 * Test whether a date, then, has gone past.
	 * 
	 * We implement this here in the trusted computing base, out of the
	 * capsec package.
	 * 
	 * @param when
	 *                date to test
	 * @return true if the current time is after then
	 */
	public abstract boolean expired(Date then);

	enum AccessType {
		VIEW_ONLY, DATA_ACCESS;

	}
	enum ApprovalStatus {
		/**
		 * Approve
		 */
		A,
		/**
		 * Deny
		 */
		D;
	}

	enum ParticipatingOrg {
		KUH, UKP, KUMC;
	}

	public DrocAccess drocAccess(Agent reviewer);

	interface DrocAccess {
		void approveSponsorship(ParticipatingOrg org, List<Pair<Integer, ApprovalStatus>> decisions);
	}

	String[] getDrocIds();
}