package edu.kumc.informatics.heron.dao;

import java.util.Date;

import edu.kumc.informatics.heron.capsec.Agent;

public interface ChalkDao {

	/**
	 * check if a user has been trained in CHALK
	 * @param userId
	 * @return expiration date of HSC training, or null if none on file
	 * @throws NotOwnerException
	 */
	Date getChalkTrainingExpireDate(Agent who);

}