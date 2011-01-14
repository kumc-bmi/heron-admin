/**
 * Dao class for HERON data access/update.
 * Avoid putting business logic especially gui related logic here.
 * Dongsheng Zhu
 */
package edu.ku.biostatistics.heron.dao;

import java.sql.Timestamp;
import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;
import org.springframework.dao.DataAccessException;
import static edu.ku.biostatistics.heron.base.StaticValues.*;

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
			log.error("error in insertSystemAccessUser()" + ex.getMessage());
		}
	}
	
	/**
	 * Insert user and project info into i2b2 database
	 * @param projId
	 * @param userId
	 * @param userRole
	 * @param fullName
	 */
	public void insertPMUser(String projId, String userId,String fullName){
		 String sql1 = "INSERT INTO PM_PROJECT_USER_ROLES(PROJECT_ID, USER_ID, USER_ROLE_CD, STATUS_CD) VALUES(?, ?, ?, 'A')";
		 String sql2 = "INSERT INTO PM_USER_DATA (USER_ID, FULL_NAME, PASSWORD, STATUS_CD) VALUES(?, ?, 'CAS', 'A')";
		 try{
			 this.getSJdbcTemplate().update(sql2, userId,fullName);
			
			 for(String userRole:userRoles){
				 this.getSJdbcTemplate().update(sql1, projId, userId, userRole);
			 }
		 }catch(DataAccessException ex)
		{
			log.error("error in insertPMUser()"+ex.getMessage());
		}
	}
	
	/**
	 * check if user already in i2b2.
	 * @param userId
	 * @return true if exist, false otherwise.
	 */
	public boolean isUserInI2b2Database(String userId){
		boolean isSigned = false;
		try{
			String sql = "select count(1) as tot from PM_USER_DATA where user_id=? and status_cd='A'";
			
			int count = this.getSJdbcTemplate().queryForInt(sql, userId);
			isSigned = count>0?true:false;
		}catch(DataAccessException ex){
			log.error("error in isUserInI2b2Database()");
		}
		return isSigned;
		
	}
	
	public void insertSponsorships(String resTitle, String resDesc,String empIds[], String nonempIds[],String expDate,String uid){
		if(empIds.length>0){
			String[] empSqls = buildQueries(resTitle,  resDesc, empIds, expDate, uid, "Y");
			this.getJdbcTemplate().batchUpdate(empSqls);
		}
		if(nonempIds.length>0){
			String[] nonEmpSqls = buildQueries(resTitle,  resDesc, nonempIds, expDate, uid, "N");
			this.getJdbcTemplate().batchUpdate(nonEmpSqls);
		}
	}
	
	private String[] buildQueries(String resTitle, String resDesc,String ids[],String expDate,String uid, String empFlag){
		String[] sqls = new String[ids.length];
		for(int i=0;i<ids.length;i++){
			StringBuffer bf = new StringBuffer("insert into heron.SPONSORSHIP(USER_ID,SPONSOR_ID,LAST_UPDT_TMST,ACCESS_TYPE,RESEARCH_TITLE,RESEARCH_DESC,EXPIRE_DATE,KUMC_EMPL_FLAG) values('");
			// prevent SQL injection
			// TODO: consider using JDBC ? params
			assert(!ids[i].contains("'"));
			assert(!uid.contains("'"));
			assert(!resTitle.contains("'"));
			assert(!resDesc.contains("'"));
			assert(!empFlag.contains("'"));
			bf.append(ids[i]);
			bf.append("','");
			bf.append(uid);
			bf.append("',sysdate,'");
			bf.append(VIEW_ONLY);
			bf.append("','");
			bf.append(resTitle);
			bf.append("','");
			bf.append(resDesc);
			bf.append("',to_date('");
			bf.append(expDate);
			bf.append("','mm/dd/yyyy'),'");
			bf.append(empFlag);
			bf.append("')");
			sqls[i] = bf.toString();
		}
		return sqls;
	}
}
