/**
 * Dao class for HERON data access/update.
 * Avoid putting business logic especially gui related logic here.
 * 
 * Dongsheng Zhu
 */
package edu.ku.biostatistics.heron.dao;

import java.sql.Timestamp;
import java.sql.Types;
import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.List;

import javax.sql.DataSource;

import org.apache.commons.collections.map.ListOrderedMap;
import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;
import org.springframework.dao.DataAccessException;
import org.springframework.jdbc.core.SqlParameter;
import org.springframework.jdbc.object.BatchSqlUpdate;

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
	
	/**
	 * Insert sponsorship data into database.
	 * @param resTitle
	 * @param resDesc
	 * @param empIds
	 * @param nonempIds
	 * @param expDate
	 * @param uid
	 */
	public void insertSponsorships(String resTitle, String resDesc,String empIds[], String nonempIds[],
			String expDate,String uid,String spnsrType,String sigName,String sigDate){
		if(empIds.length>0)
			insertDataInBatch(resTitle,  resDesc, empIds, expDate, uid, "Y",spnsrType,sigName,sigDate);
		if(nonempIds.length>0)
			insertDataInBatch(resTitle,  resDesc, nonempIds, expDate, uid, "N",spnsrType,sigName,sigDate);
		}
	

	/**
	 * insert data into table in batch.
	 * @param resTitle
	 * @param resDesc
	 * @param ids
	 * @param expDate
	 * @param uid
	 * @param empFlag
	 * @param spnsrType
	 * @throws ParseException 
	 */
	private void insertDataInBatch(String resTitle, String resDesc,String ids[],String expDate,String uid, 
			String empFlag,String spnsrType,String sigName,String sigDate){
		BatchInsert batchInsert = new BatchInsert(this.getDataSource());
		java.util.Date expDt = null;
		java.util.Date signDt = null;
		
		try{
			if(expDate!=null && !expDate.trim().equals("")){
				SimpleDateFormat fmt = new SimpleDateFormat("mm/dd/yyyy");
				expDt = fmt.parse(expDate);
			}
			if(sigDate!=null && !sigDate.trim().equals("")){
				SimpleDateFormat fmt = new SimpleDateFormat("mm/dd/yyyy");
				signDt = fmt.parse(sigDate);
			}
			for(int i=0;i<ids.length;i++){
				if(ids[i]!=null && !ids[i].trim().equals(""))
					batchInsert.update(new Object[]{ids[i],uid,spnsrType,resTitle,resDesc,expDt,empFlag,sigName,signDt});
			}
			batchInsert.flush();
		}catch(Exception ex){
			log.error("error in insertDataInBatch():"+ex.getMessage());
		}
	}
	
	class BatchInsert extends BatchSqlUpdate {
		  private static final String SQL = "insert into heron.SPONSORSHIP(UNIQ_ID,USER_ID,SPONSOR_ID,LAST_UPDT_TMST,"+
		  	"ACCESS_TYPE,RESEARCH_TITLE,RESEARCH_DESC,EXPIRE_DATE,KUMC_EMPL_FLAG,SIGNATURE,SIGNED_DATE) "+
		  	"values (heron.seq_sponsorship.nextval,?, ?, sysdate, ?, ?,?,?,?,?,?)";

		  BatchInsert(DataSource dataSource) {
		    super(dataSource, SQL);
		    declareParameter(new SqlParameter(Types.VARCHAR));
		    declareParameter(new SqlParameter(Types.VARCHAR));
		    declareParameter(new SqlParameter(Types.VARCHAR));
		    declareParameter(new SqlParameter(Types.VARCHAR));
		    declareParameter(new SqlParameter(Types.VARCHAR));
		    declareParameter(new SqlParameter(Types.DATE));
		    declareParameter(new SqlParameter(Types.VARCHAR));
		    declareParameter(new SqlParameter(Types.VARCHAR));
		    declareParameter(new SqlParameter(Types.DATE));
		    setBatchSize(100);
		}
	}
	
	/**
	 * get approver's group/org id
	 * @param uid
	 * @return string (approver's group/org id
	 */
	public String getApproverGroup(String uid){
		String grp = null;
		try{
			String sql = "select org from heron.DROC_REVIEWERS where user_id=? and status='A'";
			
			List aList = this.getSJdbcTemplate().queryForList(sql, uid);
			if(aList!=null && aList.size()>0)
				grp =  ((ListOrderedMap)aList.get(0)).get("ORG")+"";
		}catch(DataAccessException ex){
			log.error("error in getApprovalGroup()");
		}
		return grp;
	}
	
	/**
	 * get a list of sponsorship info from database.
	 * @param type
	 * @param org
	 * @return a list of sponsorship info from database
	 */
	public List getSponsorshipForApproval(String type,String org){
		String sql = "select UNIQ_ID,USER_ID,SPONSOR_ID,RESEARCH_TITLE,RESEARCH_DESC,EXPIRE_DATE from HERON.sponsorship s"+
			" where ACCESS_TYPE='"+type+"' and s.expire_date>sysdate ";
		if(org.equals("KUMC"))
			sql += " and (KUMC_APPROVAL_STATUS is null or KUMC_APPROVAL_STATUS<>'A')";
		else if(org.equals("UKP"))
			sql += " and (UKP_APPROVAL_STATUS is null or  UKP_APPROVAL_STATUS<>'A')";
		else if(org.equals("KUH"))
			sql += " and (KUH_APPROVAL_STATUS is null or KUH_APPROVAL_STATUS<>'A')"+
			" order by research_title";
		return this.getJdbcTemplate().queryForList(sql);
	}
}
