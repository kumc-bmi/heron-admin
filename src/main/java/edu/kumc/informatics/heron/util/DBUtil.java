/**
 * utility or service layer class to handle db related tasks.
 * Not limited to one database/schema. GUI/Data related business logic goes here.
 * 
 * Dongsheng Zhu
 */
package edu.kumc.informatics.heron.util;

import java.util.List;
import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.Enumeration;
import java.util.Vector;
import java.sql.Date;
import java.sql.Timestamp;

import javax.inject.Inject;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpSession;

import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;

import edu.kumc.informatics.heron.dao.ChalkDao;
import edu.kumc.informatics.heron.dao.HeronDBDao;
import edu.kumc.informatics.heron.servlet.SponsorshipServlet;
import static edu.kumc.informatics.heron.base.StaticValues.*;

@Deprecated
public class DBUtil {
	private HeronDBDao heronDao;
	private ChalkDao chalkDao;
	private BasicUtil bUtil = new BasicUtil();
	//can have other dao too...
	private Log log = LogFactory.getLog(getClass());

        public static final class Beans {
                String USER_ACCESS_DATA = "userAccessData";
        }

        @Inject
	public DBUtil(HeronDBDao h, ChalkDao ch){
		heronDao = h;
		chalkDao = ch;
	}

	
	/**
	 * get a string with ids already sponsored
	 * @param empls
	 * @param nonempls
	 * @param projTitle
	 * @param projDesc
	 * @return string with ids already sponsored in heron
	 */
	public String isSponsoredCheck(List<String> ids,String projTitle,String projDesc,String spnsrType){

		return heronDao.getSponsoredIds(Functional.mkString(ids, spnsrType),projTitle,projDesc,spnsrType);
	}
}
