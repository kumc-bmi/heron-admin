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
import java.util.Date;
import java.util.GregorianCalendar;
import java.util.List;
import java.util.Map;
import java.util.Vector;

import org.apache.commons.collections.map.ListOrderedMap;
import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;
import org.springframework.dao.DataAccessException;
import org.springframework.jdbc.core.simple.SimpleJdbcDaoSupport;

import edu.kumc.informatics.heron.capsec.Agent;
import edu.kumc.informatics.heron.dao.HeronDao.DrocAccess;
import edu.kumc.informatics.heron.util.Functional.Pair;
import static edu.kumc.informatics.heron.base.StaticValues.*;

public class HeronDBDao extends SimpleJdbcDaoSupport implements HeronDao {

        public static final String beanName = "heronDao";


        private final Log log = LogFactory.getLog(HeronDBDao.class);
	
	/* (non-Javadoc)
         * @see edu.kumc.informatics.heron.dao.HeronDao#isUserAgreementSigned(edu.kumc.informatics.heron.capsec.Agent)
         */
	@Override
        public boolean isUserAgreementSigned(Agent user) throws DataAccessException{
	        String sql = "select count(1) as tot from heron.system_access_users where user_id=?";
			
	        return this.getSimpleJdbcTemplate().queryForInt(sql, user.getUserId()) > 0;
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
		//FIXME try{
			String sql = "select org from heron.DROC_REVIEWERS where user_id=? and status='A'";
			
			@SuppressWarnings("rawtypes")
			List aList = this.getSimpleJdbcTemplate().queryForList(sql, uid);
			if(aList!=null && aList.size()>0)
				grp =  ((ListOrderedMap)aList.get(0)).get("ORG")+"";
		//}catch(DataAccessException ex){
		//	log.error("error in getApprovalGroup()");
		//}
		return grp;
	}
	
	public DrocAccess drocAccess(Agent reviewer) {
		return new DBDrocAccess(reviewer);
	}

	public class DBDrocAccess implements DrocAccess {
		public DBDrocAccess(Agent reviewer) {
			_reviewer = reviewer;
		}

		private final Agent _reviewer;

		/**
		 * get a list of sponsorship info from database. TODO: normalize
		 * XYZ_APPROVAL_STATUS
		 * 
		 * @param type
		 * @param org
		 * @return a list of sponsorship info from database
		 */
		public List<Map<String, Object>> getSponsorshipForApproval(
		                AccessType type, ParticipatingOrg org) {
			// TODO: consider a rowmapper and a real type for sponsorships
			String sql = "select SPONSORSHIP_ID,USER_ID,SPONSOR_ID,RESEARCH_TITLE,RESEARCH_DESC,EXPIRE_DATE,USER_DESC "
			                + "from HERON.sponsorship s"
			                + " where ACCESS_TYPE=? and (s.expire_date is null or s.expire_date>sysdate) and "
			                + org.toString()
			                + "_APPROVAL_STATUS is null or "
			                + org.toString()
			                + "_APPROVAL_STATUS='D')"
			                + " order by research_title";
			return HeronDBDao.this.getSimpleJdbcTemplate()
			                .queryForList(sql, type.toString());
		}

		/**
		 * approve sponsorships
		 * 
		 * @param org
		 * @param ids
		 * @param vals
		 * @param uid
		 */
		public void approveSponsorship(ParticipatingOrg org,
		                List<Pair<Integer, ApprovalStatus>> decisions) {
			// TODO: normalize database
			// TODO: look into Spring API for nicer batch update idiom.
			String SQL = "update heron.SPONSORSHIP set LAST_UPDT_TMST=sysdate,"
			                + org.toString()
			                + "_APPROVAL_STATUS=?,"
			                + org.toString()
			                + "_APPROVED_BY=?,"
			                + org.toString()
			                + "_APPROVAL_TMST =sysdate where SPONSORSHIP_ID =?";
			SponsorshipApprovalBatchUpdate batchUpdate = new SponsorshipApprovalBatchUpdate(
			                HeronDBDao.this.getDataSource(), SQL);

			for (Pair<Integer, ApprovalStatus> d : decisions) {
				batchUpdate.update(new Object[] {
				                d.getRight().toString(),
				                _reviewer.getUserId(),
				                // count on the database to coerce string to int
				                d.getLeft().toString()});
			}
			batchUpdate.flush();
		}

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
	
	@Override
        public boolean isViewOnlyUserApproved(Agent who) {
		//TODO: normalize database using org table
		String sql = "select user_id from heron.SPONSORSHIP where user_id=?"
		                + " and (expire_date is null or expire_date>sysdate) and access_type='VIEW_ONLY' "
		                + " and (kuh_approval_status ='A' and kumc_approval_status ='A' and ukp_approval_status ='A')";
		return this.getSimpleJdbcTemplate().queryForList(sql, who.getUserId())
		                .size() > 0;
	}
	
	/**
	 * get an array of droc user ids
	 * @return string array of ids
	 */
	@Override
	public String[] getDrocIds(){
		String sql = "select distinct user_id from heron.droc_reviewers where status ='A'";
		List aList = this.getJdbcTemplate().queryForList(sql);
		String[] results = new String[aList.size()];
		for(int i=0;i<aList.size();i++){
			results[i] = ((ListOrderedMap)aList.get(i)).get("USER_ID")+"";
		}
		return results;
	}
	
	/* (non-Javadoc)
         * @see edu.kumc.informatics.heron.dao.HeronDao#isUserExecutive(edu.kumc.informatics.heron.capsec.Agent)
         */
	@Override
        public boolean isUserExecutive(Agent who){
		String sql = "select count(*) from heron.exec_group where user_id=? " +
		                "and status ='A'";
		return this.getSimpleJdbcTemplate().queryForInt(sql, who.getUserId()) > 0;
	}
	
	/**
	 * retrieve sponsorship approval info
	 * @param spnId
	 * @return string[] of sponsorship approval info
	 */
	public String[] getUserApproveInfo(int spnId){
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
	public String[] getSponsorshipUserInfo(int spnId){
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
	
	/* (non-Javadoc)
         * @see edu.kumc.informatics.heron.dao.HeronDao#disclaimer(edu.kumc.informatics.heron.capsec.Agent)
         */
	@Override
        public Disclaimer disclaimer(final Agent who) {
	        return new Disclaimer(who);
	}

	public final class Disclaimer {
                Disclaimer(final Agent who) {
                        _who = who;
                }

                private final Agent _who;

                /**
                 * check if user has acknowledged the most recent disclaimer
                 * 
                 * @param uid
                 * @return true if user has acknowledged the most recent
                 *         disclaimer
                 */
                public boolean wasRead() {
                        String sql = "select count(1) from HERON.ACKNOWLEDGED_DISCLAIMERS ad, HERON.disclaimers dis "
                                        + "where ad.user_id=? and ad.disclaimer_id=dis.disclaimer_id and dis.is_recent=1";
                        return HeronDBDao.this.getJdbcTemplate().queryForInt(
                                        sql, new Object[] { _who.getUserId() }) > 0;
                }

                /**
                 * Record acknowledgement of the recent disclaimer(s)
                 */
                public void recordAckowledgement() {
                        String sql = "insert into HERON.ACKNOWLEDGED_DISCLAIMERS(user_id,disclaimer_id,acknowledge_tmst)"
                                        + "select ?,disclaimer_id,sysdate from HERON.DISCLAIMERS where is_recent=1";
                        HeronDBDao.this.getJdbcTemplate().update(sql,
                                        new Object[] { _who.getUserId() });
                }
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

	/* (non-Javadoc)
         * @see edu.kumc.informatics.heron.dao.HeronDao#expired(java.util.Date)
         */
	@Override
        public boolean expired(Date then) {
		GregorianCalendar CE = new GregorianCalendar();
		return CE.after(then);
        }

}
