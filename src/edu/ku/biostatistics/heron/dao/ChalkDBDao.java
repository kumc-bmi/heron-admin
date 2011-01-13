/**
 *Dao class for CHALK data access.
 * Avoid putting business logic especially gui related logic here.
 * Dongsheng Zhu
 */
package edu.ku.biostatistics.heron.dao;

import java.sql.Date;

import org.springframework.dao.DataAccessException;

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
	public Date checkChalkTraining(String userId){
		boolean isSigned = false;
		try{
			String sql = "select count(1) as tot from heron.system_access_users where user_id=?";
			
			int count = this.getSJdbcTemplate().queryForInt(sql, userId);
			isSigned = count>0?true:false;
		}catch(DataAccessException ex){
			//log.error("error in isUserAgreementSigned()");
		}
		return null;
	}
}
