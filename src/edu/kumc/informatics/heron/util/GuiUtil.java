package edu.kumc.informatics.heron.util;

import java.util.List;

import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;
import org.apache.commons.collections.map.ListOrderedMap;
import org.w3c.dom.Document;
import org.w3c.dom.NamedNodeMap;
import org.w3c.dom.Node;
import org.w3c.dom.NodeList;

import edu.harvard.i2b2.common.util.xml.XMLUtil;
import edu.kumc.informatics.heron.dao.HeronDBDao;
import edu.kumc.informatics.heron.dao.HeronReportsDao;

/**
 * build gui components. 
 * intended for simple gui build.
 * //TODO:as application getting more complicated, need to switch to better gui framework(struts/jsf)
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
				String uniqId = ((ListOrderedMap)aMap).get("SPONSORSHIP_ID")+"";
				String userId = ((ListOrderedMap)aMap).get("USER_ID")+"";
				String sponsorId = ((ListOrderedMap)aMap).get("SPONSOR_ID")+"";
				String userDesc = ((ListOrderedMap)aMap).get("USER_DESC")+"";
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
					bf.append("<th>User Description</th><th>Sponsor Id</th><th>Sponsor Name</th><th>Sponsor Title</th><th>Action</th></tr>");
				}
				bf.append(rowStyle);
				bf.append(userId);
				bf.append("</td><td>");
				bf.append(userInfo[0]);
				bf.append("</td><td>");
				bf.append(userInfo[2]);
				bf.append("</td><td>");
				bf.append("null".equals(userDesc)?"&nbsp;":userDesc);
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
			bf.append("<div align=center><table class=\"heron\"><tr><th>User_Id</th><th>User_Name</th>");
			bf.append("<th>Logon_Count</th><th>Query_Count</th></tr>");
			
			for(int i=0;i<usersList.size();i++){
				Object aMap = usersList.get(i);
				String userId = ((ListOrderedMap)aMap).get("USER_ID")+"";
				String name = ((ListOrderedMap)aMap).get("user_full_name")+"";
				String sCount = ((ListOrderedMap)aMap).get("session_count")+"";
				String qCount = ((ListOrderedMap)aMap).get("query_count")+"";
	
				String rowStyle = i%2==0?"<tr class=\"d0\"><td>":"<tr class=\"d1\"><td>";
				bf.append(rowStyle);
				bf.append(userId);
				bf.append("</td><td>");
				bf.append(name);
				bf.append("</td><td>");
				bf.append(sCount);
				bf.append("</td><td>");
				if(!qCount.equals("0"))
					bf.append("<a href=\"query_report_details.jsp?uid="+userId+"\">" + qCount + "</a>");
				else 
					bf.append(qCount);
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
			bf.append("<th>Expiration</th><th>KUMC Employee</th><th>KUH Approved at</th><th>KUMC Approved at</th><th>UKP Approved at</th></tr>");
			
			for(int i=0;i<usersList.size();i++){
				Object aMap = usersList.get(i);
				String userId = ((ListOrderedMap)aMap).get("USER_ID")+"";
				String project = ((ListOrderedMap)aMap).get("research_title")+"";
				String exp = ((ListOrderedMap)aMap).get("expire_date")+"";
				String employee = ((ListOrderedMap)aMap).get("kumc_empl_flag")+"";
				String kuhTime = ((ListOrderedMap)aMap).get("kuh_approval_tmst")+"";
				String kumcTime = ((ListOrderedMap)aMap).get("kumc_approval_tmst")+"";
				String ukpTime = ((ListOrderedMap)aMap).get("ukp_approval_tmst")+"";
				String rowStyle = i%2==0?"<tr class=\"d0\"><td>":"<tr class=\"d1\"><td>";
				bf.append(rowStyle);
				bf.append(userId);
				bf.append("</td><td>");
				bf.append(project);
				bf.append("</td><td>");
				bf.append("null".equals(exp)?"&nbsp;":exp);
				bf.append("</td><td>");
				bf.append(employee);
				bf.append("</td><td>");
				bf.append(kuhTime);
				bf.append("</td><td>");
				bf.append(kumcTime);
				bf.append("</td><td>");
				bf.append(ukpTime);
				bf.append("</td></tr>");
			}
			bf.append("</table></div>");
		}
		return bf.toString();
	}
	
	/**
	 * get most recent Disclaimer
	 * @return a string (most recent Disclaimer)
	 */
	public String getRecentDisclaimer(){
		return heronDao.getRecentDisclaimer();
	}
	
	/**
	 * build user query report
	 * @param userId
	 * @return string/html
	 */
	public String getQueryReport(String userId){
		List aList = rptDao.getQueryReportInfo(userId);
		StringBuffer bf = new StringBuffer("");
		bf.append("<div align=center>Query Report for User: "+userId+"</div>");
		bf.append("<div align=center><table class=\"heron\"><tr><th>Query_Name</th><th>Query_Details</th>");
		bf.append("<th>Start</th><th>Set_Size</th><th>Real_Set_Size</th><th>Description</th></tr>");

		try{
			for(int i=0;i<aList.size();i++){
				Object aMap = aList.get(i);
				String qname = ((ListOrderedMap)aMap).get("name")+"";
				String qxml = ((ListOrderedMap)aMap).get("request_xml")+"";
				String sSize = ((ListOrderedMap)aMap).get("set_size")+"";
				String sDate = ((ListOrderedMap)aMap).get("start_date")+"";
				String rSize = ((ListOrderedMap)aMap).get("real_set_size")+"";
				String description = ((ListOrderedMap)aMap).get("description")+"";
				String rowStyle = i%2==0?"<tr class=\"d0\"><td>":"<tr class=\"d1\"><td>";
				Document doc = XMLUtil.convertStringToDOM(qxml);
				NodeList nList = doc.getElementsByTagName("panel");
				
				bf.append(rowStyle);
				bf.append(qname);
				bf.append("</td><td>");
				
				for(int j=0;j<nList.getLength();j++){
					bf.append("Panel "+j+": <br>");
					Node node = nList.item(j);
					NodeList nlist2 = node.getChildNodes();
					for(int k=0;k<nlist2.getLength();k++){
						Node node2 = nlist2.item(k);
						if(node2.getNodeName().equals("item")){
							NodeList nList3 = node2.getChildNodes();
							for(int m=0;m<nList3.getLength();m++){
								Node node3 = nList3.item(m);
								if(node3.getNodeName().equals("item_name")){
									bf.append("item_name: "+node3.getFirstChild().getNodeValue()+";");
								}
								else if(node3.getNodeName().equals("tooltip")){
									bf.append("tooltip: "+node3.getFirstChild().getNodeValue()+";<br>");
								}
									
							}
						}
							
					}
				}
	
				bf.append("</td><td>");
				bf.append(sDate);
				bf.append("</td><td>");
				bf.append(sSize);
				bf.append("</td><td>");
				bf.append(rSize);
				bf.append("</td><td>");
				bf.append(description.equals("null")?"":description);
				bf.append("</td></tr>");
			}
			bf.append("</table></div>");
			return bf.toString();
		}
		catch(Exception ex){
			return "Error parsing request xml";
		}
	}
}
