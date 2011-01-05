/**
 * utility or service layer class to handle db related tasks.
 * Not limited to one database/schema.
 * 
 * Dongsheng Zhu
 */
package edu.ku.biostatistics.heron.util;

import java.text.DateFormat;
import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.sql.Timestamp;

import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpSession;

import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;

import edu.ku.biostatistics.heron.dao.DBBaseDao;
import edu.ku.biostatistics.heron.dao.HeronDBDao;
import static edu.ku.biostatistics.heron.base.StaticValues.*;

public class DBUtil {
	private HeronDBDao heronDao;
	//can have other dao too...
	private static Log log = LogFactory.getLog(DBUtil.class);
	
	public DBUtil(){
		heronDao = new HeronDBDao();
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
		String userName = session.getAttribute(USER_NAME)+"";
		String signature = request.getParameter("txtName");
		String signDate = request.getParameter("txtSignDate");
		try{
			Long ms = new SimpleDateFormat("mm/dd/yyyy").parse(signDate).getTime();
			heronDao.insertSystemAccessUser(userId, userName, signature, new Timestamp(ms));
		}
		catch(ParseException ex){
			log.error("error in insertSystemAccessUser() parsing date");
		}
	}
}
