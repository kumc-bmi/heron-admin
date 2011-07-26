/**
 * Dao class for HERON data access/update.
 * Avoid putting business logic especially gui related logic here.
 * 
 * Dongsheng Zhu
 */
package edu.kumc.informatics.heron.dao;

import java.sql.Timestamp;
import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.List;
import java.util.Vector;

import org.apache.commons.collections.map.ListOrderedMap;
import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;
import org.springframework.dao.DataAccessException;
import org.springframework.jdbc.core.simple.SimpleJdbcDaoSupport;
import static edu.kumc.informatics.heron.base.StaticValues.*;

public class HeronDBDao extends SimpleJdbcDaoSupport {
	private final Log log = LogFactory.getLog(HeronDBDao.class);
	
	/**
	 * check if user has signed system access agreement.
	 * @param userId
	 * @return true if yes, false otherwise
	 */
	public boolean isUserAgreementSigned(String userId){
		boolean isSigned = false;
		try{
			String sql = "select count(1) as tot from heron.system_access_users where user_id=?";
			
			int count = this.getSimpleJdbcTemplate().queryForInt(sql, userId);
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
			this.getSimpleJdbcTemplate().update(sql,  userId, userName, sigature, signDate);
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
			 this.getSimpleJdbcTemplate().update(sql2, userId,fullName);
			
			 for(String userRole:userRoles){
				 this.getSimpleJdbcTemplate().update(sql1, projId, userId, userRole);
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
			
			int count = this.getSimpleJdbcTemplate().queryForInt(sql, userId);
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
			String expDate,String uid,String spnsrType,String sigName,String sigDate,String[] nonEmpDescArray) throws Exception{
		if(empIds !=null && empIds.length>0)
			insertDataInBatch(resTitle,  resDesc, empIds, expDate, uid, "Y",spnsrType,sigName,sigDate,null);
		if(nonempIds!=null && nonempIds.length>0)
			insertDataInBatch(resTitle,  resDesc, nonempIds, expDate, uid, "N",spnsrType,sigName,sigDate,nonEmpDescArray);
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
			String empFlag,String spnsrType,String sigName,String sigDate,String[] nonEmpDescArray) throws Exception{
		SponsorshipBatchInsert batchInsert = new SponsorshipBatchInsert(this.getDataSource());
		java.util.Date expDt = null;
		java.util.Date signDt = null;
		
		try{
			if(expDate!=null && !expDate.trim().equals("")){
				SimpleDateFormat fmt = new SimpleDateFormat("MM/dd/yyyy");
				expDt = fmt.parse(expDate);
			}
			if(sigDate!=null && !sigDate.trim().equals("")){
				SimpleDateFormat fmt = new SimpleDateFormat("MM/dd/yyyy");
				signDt = fmt.parse(sigDate);
			}
			for(int i=0;i<ids.length;i++){
				if(ids[i]!=null && !ids[i].trim().equals("")){
					String nonEmpDesc = nonEmpDescArray!=null?nonEmpDescArray[i]:"null";
					batchInsert.update(new Object[]{ids[i],uid,spnsrType,resTitle,resDesc,expDt,empFlag,sigName,signDt,nonEmpDesc});
				}
			}
			batchInsert.flush();
		}catch(Exception ex){
			log.error("error in insertDataInBatch():"+ex.getMessage());
			throw ex;
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
			
			@SuppressWarnings("rawtypes")
			List aList = this.getSimpleJdbcTemplate().queryForList(sql, uid);
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
	@SuppressWarnings("rawtypes")
	public List getSponsorshipForApproval(String type,String org){
		String sql = "select SPONSORSHIP_ID,USER_ID,SPONSOR_ID,RESEARCH_TITLE,RESEARCH_DESC,EXPIRE_DATE,USER_DESC from HERON.sponsorship s"+
			" where ACCESS_TYPE='"+type+"' and (s.expire_date is null or s.expire_date>sysdate) ";
		if(org.equals("KUMC"))
			sql += " and (KUMC_APPROVAL_STATUS is null or KUMC_APPROVAL_STATUS='D')";
		else if(org.equals("UKP"))
			sql += " and (UKP_APPROVAL_STATUS is null or  UKP_APPROVAL_STATUS='D')";
		else if(org.equals("KUH"))
			sql += " and (KUH_APPROVAL_STATUS is null or KUH_APPROVAL_STATUS='D')"+
			" order by research_title";
		return this.getJdbcTemplate().queryForList(sql);
	}
	
	/**
	 * approve sponsorships
	 * @param org
	 * @param ids
	 * @param vals
	 * @param uid
	 */
	public void approveSponsorship(String org, Vector<String> ids, Vector<String> vals, String uid){
		String SQL = "update heron.SPONSORSHIP set LAST_UPDT_TMST=sysdate,";
		if("KUMC".equals(org))
			SQL += "KUMC_APPROVAL_STATUS=?,KUMC_APPROVED_BY=?,KUMC_APPROVAL_TMST ";
		else if("UKP".equals(org))
			SQL += "UKP_APPROVAL_STATUS=?,UKP_APPROVED_BY=?,UKP_APPROVAL_TMST ";
		else if("KUH".equals(org))
			SQL += "KUH_APPROVAL_STATUS=?,KUH_APPROVED_BY=?,KUH_APPROVAL_TMST ";	  
		SQL += "=sysdate where SPONSORSHIP_ID =?";
		SponsorshipApprovalBatchUpdate batchUpdate = new SponsorshipApprovalBatchUpdate(this.getDataSource(),SQL);
		
		for(int i=0;i<ids.size();i++){
				batchUpdate.update(new Object[]{vals.get(i),uid,ids.get(i)});
		}
		batchUpdate.flush();
		
	}
	
	/**
	 * retrieve users from DROC committe  and with admin  roles.
	 * @param uid
	 * @return a list of user ids
	 */
	@SuppressWarnings("rawtypes")
	public List getUserValidRoles(String uid){
		String sql = "select user_id from heron.DROC_REVIEWERS where user_id='" + uid 
			+ "' and status='A' union select user_id from pm_project_user_roles where user_id='"+
			uid + "' and user_role_cd='ADMIN' and status_cd ='A' ";
		return this.getJdbcTemplate().queryForList(sql);
	}
	
	/**
	 * check if a view_only user is sponsored and approved.
	 * @param uid
	 * @return true if  sponsored and approved.
	 */
	public boolean isViewOnlyUserApproved(String uid){
		String sql = "select user_id from heron.SPONSORSHIP where user_id='" +
			uid + "' and (expire_date is null or expire_date>sysdate) and access_type='VIEW_ONLY' " +
			" and (kuh_approval_status ='A' and kumc_approval_status ='A' and ukp_approval_status ='A')";
		return this.getJdbcTemplate().queryForList(sql).size()>0;
	}
	
	/**
	 * get an array of droc user ids
	 * @return string array of ids
	 */
	public String[] getDrocIds(){
		String sql = "select distinct user_id from heron.droc_reviewers where status ='A'";
		@SuppressWarnings("unchecked")
		List<Object> aList = this.getJdbcTemplate().queryForList(sql);
		String[] results = new String[aList.size()];
		for(int i=0;i<aList.size();i++){
			results[i] = ((ListOrderedMap)aList.get(i)).get("USER_ID")+"";
		}
		return results;
	}
	
	/**
	 * check if user an executive
	 * @param uid
	 * @return true if yes
	 */
	public boolean isUserExecutive(String uid){
		String sql = "select user_id from heron.exec_group where user_id='" +
		uid + "' and status ='A'";
		return this.getJdbcTemplate().queryForList(sql).size()>0;
	}
	
	/**
	 * retrieve sponsorship approval info
	 * @param spnId
	 * @return string[] of sponsorship approval info
	 */
	public String[] getUserApproveInfo(String spnId){
		String sql = "select user_id, sponsor_id,research_title from HERON.sponsorship where sponsorship_id="+
			spnId + " and kuh_approval_status='A' and kumc_approval_status='A' and ukp_approval_status='A'";
		@SuppressWarnings("rawtypes")
		List aList =  this.getJdbcTemplate().queryForList(sql);
		if(aList.size()>0){
			ListOrderedMap aMap = (ListOrderedMap)aList.get(0);
			return new String[]{"T",aMap.get("user_id")+"",aMap.get("sponsor_id")+"",aMap.get("research_title")+""};
		}
		else
			return new String[]{"F",null,null,null};
	}
	
	/**
	 * retrieve user id and sponsor id using a sponsorship id.
	 * @param spnId
	 * @return a string[] of user id and sponsor id
	 */
	public String[] getSponsorshipUserInfo(String spnId){
		String sql = "select user_id, sponsor_id,research_title from HERON.sponsorship where sponsorship_id="+ spnId;
		@SuppressWarnings("rawtypes")
		List aList =  this.getJdbcTemplate().queryForList(sql);
		ListOrderedMap aMap = (ListOrderedMap)aList.get(0);
		return new String[]{aMap.get("user_id")+"",aMap.get("sponsor_id")+"",aMap.get("research_title")+""};
	}
	
	/**
	 * retrieve string with ids already sponsored in heron
	 * @param idString
	 * @param projTitle
	 * @param projDesc
	 * @return string with ids
	 */
	public String getSponsoredIds(String idString, String projTitle, String projDesc,String spnsrType){
		//TODO: not ideal. better use NamedParameterJdbcTemplate, but not available for this version of spring
		String sql = "select distinct user_id from HERON.sponsorship where user_id in ("+
			idString + ") and research_title=? and research_desc=? and access_type=?";
		@SuppressWarnings("rawtypes")
		List aList =  this.getJdbcTemplate().queryForList(sql,new Object[]{projTitle,projDesc,spnsrType});
		StringBuffer bf = new StringBuffer();
		
		for(int i=0;i<aList.size();i++){
			ListOrderedMap aMap = (ListOrderedMap)aList.get(i);
			bf.append(aMap.get("user_id"));
			bf.append(" ");
		}
		return bf.toString();
	}
	
	/**
	 * check if user has acknowledged the most recent disclaimer
	 * @param uid
	 * @return true if user has acknowledged the most recent disclaimer
	 */
	public boolean isDisclaimerRead(String uid){
		String sql = "select count(1) from HERON.ACKNOWLEDGED_DISCLAIMERS ad, HERON.disclaimers dis "+
			"where ad.user_id=? and ad.disclaimer_id=dis.disclaimer_id and dis.is_recent=1";
		return this.getJdbcTemplate().queryForInt(sql, new Object[]{uid})>0;
	}
	
	/**
	 * @see DBUtil#updateDisclaimerAckowledgement
	 */
	public void updateDisclaimerAckowledgement(String uid){
		String sql = "insert into HERON.ACKNOWLEDGED_DISCLAIMERS(user_id,disclaimer_id,acknowledge_tmst)"+
			"select '"+uid+"',disclaimer_id,sysdate from HERON.DISCLAIMERS where is_recent=1";
		this.getJdbcTemplate().execute(sql);
	}
	
	/**
	 * @see DBUtil#getRecentDisclaimer
	 */
	public String getRecentDisclaimer(){
		String sql = "select disclaimer_url from HERON.DISCLAIMERS where is_recent=1";
		List aList = this.getJdbcTemplate().queryForList(sql);
		return aList.size()>0?((ListOrderedMap)aList.get(0)).get("disclaimer_url")+"":"ERROR: No Recent Disclaimer";
	}
	
	public List getSponsoredIdsById(String uid){
		String sql =  "select distinct user_id from HERON.sponsorship where sponsor_id = '" + uid + "' and expire_date>sysdate";
		return this.getJdbcTemplate().queryForList(sql);
	}
	
	public List getAllActiveIds(){
		String sql =  "select distinct user_id from HERON.sponsorship where expire_date>sysdate";
		return this.getJdbcTemplate().queryForList(sql);
	}
	
	/**
	 * @see DBUtil#termSponsorship
	 * @param id
	 * @return success message
	 */
	public String termSponsorship(String id,String action,String reason){
		String sql = "update HERON.sponsorship set expire_date = sysdate,last_updt_tmst=sysdate where user_id =?"; 
		String sql2 = "insert into HERON.sponsorship_status_change_hist(user_id,action,reason,update_timestamp)"+
			" values(?,?,?,sysdate)";
		try{
			this.getJdbcTemplate().update(sql,new String[]{id});
			this.getJdbcTemplate().update(sql2,new String[]{id,action,reason});
			return "User id "+ id + " is terminated successfully.";
		}catch(Exception ex){
			return "User termination failed.";
		}
	}
}
