/**
 *Dao class for CHALK data access.
 * 
 * Dongsheng Zhu
 */
package edu.ku.biostatistics.heron.dao;

public class ChalkDBDao extends DBBaseDao{
	public ChalkDBDao()
	{
		super("java:ChalkDS");
	}
	
	/**
	 * check if a user has been trained in CHALK
	 * @param userId
	 * @return
	 */
	public int checkChalkTraining(String userId){
		return 1;
	}
}
