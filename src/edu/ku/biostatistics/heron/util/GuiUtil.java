package edu.ku.biostatistics.heron.util;

import java.util.List;

import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;
import org.apache.commons.collections.map.ListOrderedMap;
import edu.ku.biostatistics.heron.dao.HeronDBDao;
import edu.ku.biostatistics.heron.dao.HeronReportsDao;

/**
 * build gui components. 
 * 
 * @author dzhu
 *
 */
public class GuiUtil {
	private HeronDBDao heronDao;
	private HeronReportsDao rptDao;
	private LdapUtil lUtil;
	private static Log log = LogFactory.getLog(DBUtil.class);
	
	public GuiUtil(){
		heronDao = new HeronDBDao();
		lUtil = new LdapUtil();
		rptDao = new HeronReportsDao();
	}
	
	/**
	 * build sponsorship display component
	 * @param type
	 * @param uid
	 * @return a string of html
	 */
	public String getSponsorship(String type,String uid){
		StringBuffer bf = new StringBuffer("");
		String org = heronDao.getApproverGroup(uid);
		
		if(org == null)
			bf.append("<div class=\"h5red\">Sorry, seems you are not allowed to use this functionality.</div>");
		else{
			List spnsrList = heronDao.getSponsorshipForApproval(type,org);
			String prevTitle ="";
			String curTitle ="";
			if(spnsrList==null || spnsrList.size()==0)
				return "<div align=center>There is no users need to be approved at this time.</div>";
			bf.append("<input type=hidden name=\"hidOrg\" value=\"" + org + "\">");
			
			for(int i=0;i<spnsrList.size();i++){
				Object aMap = spnsrList.get(i);
				curTitle = ((ListOrderedMap)aMap).get("RESEARCH_TITLE")+"";
				String uniqId = ((ListOrderedMap)aMap).get("UNIQ_ID")+"";
				String userId = ((ListOrderedMap)aMap).get("USER_ID")+"";
				String sponsorId = ((ListOrderedMap)aMap).get("SPONSOR_ID")+"";
				String[] userInfo = lUtil.getUserInfo(userId);
				String[] spnsrInfo = lUtil.getUserInfo(sponsorId);
				String rowStyle = i%2==0?"<tr class=\"d0\"><td>":"<tr class=\"d1\"><td>";
				if(!prevTitle.equals(curTitle)){
					bf.append("<p></p><div>Research Title: ");
					bf.append(curTitle);
					bf.append("</div>");
					bf.append("<div>Research Description: ");
					bf.append(((ListOrderedMap)aMap).get("RESEARCH_DESC"));
					bf.append("</div><table class=\"heron\"><tr><th>User Id</th><th>User Name</th><th>User Title</th>");
					bf.append("<th>Sponsor Id</th><th>Sponsor Name</th><th>Sponsor Title</th><th>Action</th></tr>");
				}
				bf.append(rowStyle);
				bf.append(userId);
				bf.append("</td><td>");
				bf.append(userInfo[0]);
				bf.append("</td><td>");
				bf.append(userInfo[2]);
				bf.append("</td><td>");
				bf.append(sponsorId);
				bf.append("</td><td>");
				bf.append(spnsrInfo[0]);
				bf.append("</td><td>");
				bf.append(spnsrInfo[2]);
				bf.append("</td><td>");
				bf.append("<input type=radio name=\"rad_");
				bf.append(uniqId);
				bf.append("\" value=\"A\">Approve<input type=radio name=\"rad_");
				bf.append(uniqId);
				bf.append("\" value=\"R\">Reject<input type=radio name=\"rad_");
				bf.append(uniqId);
				bf.append("\" value=\"D\">Defer</td></tr>");
				
				if(i<spnsrList.size()-1){
					Object nextMap = spnsrList.get(i+1);
					String nextTitle= nextMap!=null?((ListOrderedMap)nextMap).get("RESEARCH_TITLE")+"":"";
				
					if(!nextTitle.equals(curTitle))
						bf.append("</table>");
				}
				else if(i==spnsrList.size()-1)
					bf.append("</table>");
				prevTitle = curTitle;
			}
		}
		
		return bf.toString();
	}
	
	/**
	 * build heron system users report
	 * @param uid
	 * @return String/html of the users
	 */
	public String getHeronSystemUsers(String uid){
		StringBuffer bf = new StringBuffer("");
		List roles = heronDao.getUserValidRoles(uid);
		
		if(roles.size()<1){
			bf.append("<div class=\"h5red\">Sorry, seems you are not allowed to use this functionality.</div>");
		}
		else{
			List usersList = rptDao.getHeronSystemUsers();
			if(usersList==null || usersList.size()==0)
				return "<div align=center>There is no users at this time.</div>";
			bf.append("<div align=center>Total Users Count: "+usersList.size()+"</div>");
			bf.append("<div align=center><table class=\"heron\"><tr><th>User Id</th><th>User Name</th></tr>");
			
			for(int i=0;i<usersList.size();i++){
				Object aMap = usersList.get(i);
				String userId = ((ListOrderedMap)aMap).get("USER_ID")+"";
				String name = ((ListOrderedMap)aMap).get("user_full_name")+"";
				String rowStyle = i%2==0?"<tr class=\"d0\"><td>":"<tr class=\"d1\"><td>";
				bf.append(rowStyle);
				bf.append(userId);
				bf.append("</td><td>");
				bf.append(name);
				bf.append("</td></tr>");
			}
			bf.append("</table></div>");
		}
		return bf.toString();
	}
	
	/**
	 * build approved users' display html/string
	 * @param type type of users
	 * @param uid User id of the current user
	 * @return a String/html with users' info
	 */
	public String getApprovedUsers(String type,String uid){
		StringBuffer bf = new StringBuffer("");
		List roles = heronDao.getUserValidRoles(uid);
		
		if(roles.size()<1){
			bf.append("<div class=\"h5red\">Sorry, seems you are not allowed to use this functionality.</div>");
		}
		else{
			List usersList = rptDao.getApprovedUsers(type);
			if(usersList==null || usersList.size()==0)
				return "<div align=center>There is no users at this time.</div>";
			bf.append("<div align=center>Total Users Count: "+usersList.size()+"</div>");
			bf.append("<div align=center><table class=\"heron\"><tr><th>User Id</th><th>Research Project</th>");
			bf.append("<th>Expiration</th><th>KUMC Employee</th></tr>");
			
			for(int i=0;i<usersList.size();i++){
				Object aMap = usersList.get(i);
				String userId = ((ListOrderedMap)aMap).get("USER_ID")+"";
				String project = ((ListOrderedMap)aMap).get("research_title")+"";
				String exp = ((ListOrderedMap)aMap).get("expire_date")+"";
				String employee = ((ListOrderedMap)aMap).get("kumc_empl_flag")+"";
				String rowStyle = i%2==0?"<tr class=\"d0\"><td>":"<tr class=\"d1\"><td>";
				bf.append(rowStyle);
				bf.append(userId);
				bf.append("</td><td>");
				bf.append(project);
				bf.append("</td><td>");
				bf.append(exp);
				bf.append("</td><td>");
				bf.append(employee);
				bf.append("</td></tr>");
			}
			bf.append("</table></div>");
		}
		return bf.toString();
	}
}
