/**
 * utility or service layer class to handle db related tasks.
 * Not limited to one database/schema. GUI/Data related business logic goes here.
 * 
 * Dongsheng Zhu
 */
package edu.kumc.informatics.heron.util;

import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.Enumeration;
import java.util.GregorianCalendar;
import java.util.Vector;
import java.sql.Date;
import java.sql.Timestamp;

import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpSession;

import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;

import edu.kumc.informatics.heron.dao.ChalkDBDao;
import edu.kumc.informatics.heron.dao.HeronDBDao;
import static edu.kumc.informatics.heron.base.StaticValues.*;

public class DBUtil {
	private HeronDBDao heronDao;
	private ChalkDBDao chalkDao;
	private BasicUtil bUtil = new BasicUtil();
	//can have other dao too...
	private static Log log = LogFactory.getLog(DBUtil.class);
	
	public DBUtil(){
		heronDao = new HeronDBDao();
		chalkDao = new ChalkDBDao();
	}
	
	/**
	 * check if user has signed system access agreement.
	 * @param userId
	 * @return true if yes, false otherwise
	 */
	public boolean isUserAgreementSigned(String userId){
		return heronDao.isUserAgreementSigned(userId);
	}
	
	/**
	 * add one entry to system_access_users table.
	 * @param userId
	 * @param userName
	 * @param sigature
	 * @param signDate
	 */
	public void insertSystemAccessUser(HttpServletRequest request)
	{		
		String userId = request.getRemoteUser();
		HttpSession session = request.getSession();
		String userName = session.getAttribute(USER_FULL_NAME)+"";
		String signature = request.getParameter("txtName");
		String signDate = request.getParameter("txtSignDate");
		try{
			Long ms = new SimpleDateFormat("MM/dd/yyyy").parse(signDate).getTime();
			heronDao.insertSystemAccessUser(userId, userName, signature, new Timestamp(ms));
		}
		catch(ParseException ex){
			log.error("error in insertSystemAccessUser() parsing date");
		}
	}
	
	/**
	 * check if user already in i2b2.
	 * @param userId
	 * @return true if exist, false otherwise.
	 */
	public boolean isUserInI2b2Database(String userId){
		return heronDao.isUserInI2b2Database(userId);
	}
	
	/**
	 * Insert user and project info into i2b2 database
	 * @param request a HttpServletRequest
	 */
	public void insertPMUser(HttpServletRequest request){
		String projId = StaticDataUtil.getSoleInstance().getProperties().getProperty(USER_PROJ);
		String userId = request.getRemoteUser();
		String fullName = request.getSession().getAttribute(USER_FULL_NAME)+"";
		heronDao.insertPMUser(projId, userId, fullName);
	}
	
	/**
	 * check if a user has been properly trained in CHALK 
	 * @param request a HttpServletRequest
	 * @return training expiration date.
	 */
	public Date checkChalkTraining(HttpServletRequest request){
		return chalkDao.getChalkTrainingExpireDate(request.getRemoteUser());
	}
	
	/**
	 * insert sponsorship data into database.
	 * @param request a HttpServletRequest.
	 */
	public void insertSponsorships(HttpServletRequest request)throws Exception{
		String resTitle = request.getParameter("txtRTitle");
		String resDesc = request.getParameter("resDesc");
		String empIds = request.getParameter("empIds");
		String nonempIds = request.getParameter("nonempIds");
		String expDate = request.getParameter("expDate");
		String spnsrType = request.getParameter("spnsr_type");
		String sigName = request.getParameter("txtName");
		String sigDate = request.getParameter("txtSignDate");
		String uid = request.getRemoteUser();
		String[] empIdArray = empIds.split(";");
		HttpSession session = request.getSession();
		String[] nonEmpIdArray = (String[])session.getAttribute(NON_EMP_IDS);
		String[] nonEmpDescArray = (String[])session.getAttribute(NON_EMP_DESCS);
		heronDao.insertSponsorships(resTitle,resDesc,empIdArray,nonEmpIdArray,expDate,uid,spnsrType,sigName,sigDate,nonEmpDescArray);
	}
	
	/**
	 * approve sponsorships.
	 * @param request
	 * @return empty string if success, else a warning message.
	 */
	public String approveSponsorship(HttpServletRequest request){
		String result = "Approved Successfully.";
		boolean anyChecked = false;
		Vector<String> ids = new Vector<String>();
		Vector<String> vals = new Vector<String>();
		@SuppressWarnings("unchecked")
		Enumeration<String> names = request.getParameterNames();
		String org = request.getParameter("hidOrg");
		String uid = request.getRemoteUser();
		
		while(names.hasMoreElements()){
			String param = names.nextElement()+"";
			if(param.startsWith("rad_")){
				String id = param.substring(4);
				String val = request.getParameter(param);
				if(val!=null){
					anyChecked = true;
					ids.add(id);
					vals.add(val);
				}
			}
		}
		if(anyChecked){
			heronDao.approveSponsorship(org, ids, vals, uid);
			notifyUserApprovedOrRejected(ids,vals);
		}
		else
			result = "you did not check anyone to approve.";
		return  result;
	}
	
	/**
	 * check if a user is sponsored and approved
	 * @param uid
	 * @return true if yes, false otherwise
	 */
	public boolean isViewOnlyUserApproved(String uid){
		return heronDao.isViewOnlyUserApproved(uid);
	}
	
	/**
	 * get droc member ids
	 * @return droc member ids as String[]
	 */
	public String[] getDrocIds(){
		return heronDao.getDrocIds();
	}
	
	/**
	 * check if user active in exec_group table
	 * @param uid
	 * @return true if user active in exec_group table.
	 */
	public boolean isUserExecutive(String uid){
		return heronDao.isUserExecutive(uid);
	}
	
	/**
	 * notify user and sponsor if request/sponsorship get rejected or approved
	 * @param ids
	 * @param vals
	 */
	private void notifyUserApprovedOrRejected(Vector ids, Vector vals){
		for(int i=0;i<ids.size();i++){
			String val = vals.get(i)+"";
			
			if(val.equals("A")){
				String[] approveInfo = heronDao.getUserApproveInfo(ids.get(i)+"");
				if(approveInfo[0]=="T"){
					bUtil.notifyUserApprovedOrRejected(approveInfo[1],approveInfo[2],"A");
				}
			}
			else if (val.equals("R")){
				String[] spsrInfo = heronDao.getSponsorshipUserInfo(ids.get(i)+"");
				bUtil.notifyUserApprovedOrRejected(spsrInfo[0],spsrInfo[1],"R");
			}
		}
	}
}
