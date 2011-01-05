/**
 * Dao class for HERON data access/update.
 * Dongsheng Zhu
 */
package edu.ku.biostatistics.heron.dao;

import java.sql.Timestamp;
import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;
import org.springframework.dao.DataAccessException;

public class HeronDBDao extends DBBaseDao{
	private static Log log = LogFactory.getLog(HeronDBDao.class);

	public HeronDBDao(){
		super("java:PMBootStrapDS");
	}
	
	/**
	 * check if user has signed system access agreement.
	 * @param userId
	 * @return true if yes, false otherwise
	 */
	public boolean isUserAgreementSigned(String userId){
		boolean isSigned = false;
		try{
			String sql = "select count(1) as tot from heron.system_access_users where user_id=?";
			
			int count = this.getSJdbcTemplate().queryForInt(sql, userId);
			isSigned = count>0?true:false;
		}catch(DataAccessException ex){
			log.error("error in isUserAgreementSigned()");
		}
		return isSigned;
		
	}
	
	/**
	 * add one entry to system_access_users table.
	 * @param userId
	 * @param userName
	 * @param sigature
	 * @param signDate
	 */
	public void insertSystemAccessUser(String userId,String userName,String sigature,Timestamp signDate){
		String sql = "insert into heron.system_access_users(USER_ID,USER_FULL_NAME,SIGNATURE,SIGNED_DATE,LAST_UPDT_TMST) values(?,?,?,?,sysdate)";

		try{
			this.getSJdbcTemplate().update(sql,  userId, userName, sigature, signDate);
		}catch(DataAccessException ex)
		{
			log.error("error in insertSystemAccessUser()");
		}
	}
}
