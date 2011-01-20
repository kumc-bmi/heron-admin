package edu.ku.biostatistics.heron.util;

import java.util.List;

import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;
import org.apache.commons.collections.map.ListOrderedMap;
import edu.ku.biostatistics.heron.dao.HeronDBDao;

/**
 * 
 * @author dzhu
 *
 */
public class GuiUtil {
	private HeronDBDao heronDao;
	private LdapUtil lUtil;
	private static Log log = LogFactory.getLog(DBUtil.class);
	
	public GuiUtil(){
		heronDao = new HeronDBDao();
		lUtil = new LdapUtil();
	}
	
	public String getSponsorship(String type,String uid){
		StringBuffer bf = new StringBuffer("");
		String org = heronDao.getApproverGroup(uid);
		
		if(org == null)
			bf.append("<div class=\"h5red\">Sorry, seems you are not allowed to use this functionality.</div>");
		else{
			List spnsrList = heronDao.getSponsorshipForApproval(type,org);
			String prevTitle ="";
			String curTitle ="";
			
			for(int i=0;i<spnsrList.size();i++){
				Object aMap = spnsrList.get(i);
				curTitle = ((ListOrderedMap)aMap).get("RESEARCH_TITLE")+"";
				String userId = ((ListOrderedMap)aMap).get("USER_ID")+"";
				String sponsorId = ((ListOrderedMap)aMap).get("SPONSOR_ID")+"";
				String[] userInfo = lUtil.getUserInfo(userId);
				String[] spnsrInfo = lUtil.getUserInfo(sponsorId);
				
				if(!prevTitle.equals(curTitle)){
					bf.append("<div>Research Title: ");
					bf.append(curTitle);
					bf.append("</div>");
					bf.append("<div>Research Description: ");
					bf.append(((ListOrderedMap)aMap).get("RESEARCH_DESC"));
					bf.append("</div><table class=\"heron\"><tr><th>User Id</th><th>User Name</th><th>User Title</th>");
					bf.append("<th>Sponsor Id</th><th>Sponsor Name</th><th>Sponsor Title</th><th>Approve</th></tr>");
				}
				bf.append("<tr><td>");
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
				bf.append("<input type=radio name=\"");
				bf.append(curTitle+"_"+userId+"_"+sponsorId);
				bf.append("\" value=\"Approve\">Approve<input type=radio name=\"");
				bf.append(curTitle+"_"+userId+"_"+sponsorId);
				bf.append("\" value=\"Decline\">Decline<input type=radio name=\"");
				bf.append(curTitle+"_"+userId+"_"+sponsorId);
				bf.append("\" value=\"Defer\">Defer decision</td></tr>");
				
				if(i<spnsrList.size()-1){
					Object nextMap = spnsrList.get(i+1);
					String nextTitle= nextMap!=null?((ListOrderedMap)nextMap).get("RESEARCH_TITLE")+"":"";
				
					if(!nextTitle.equals(curTitle))
						bf.append("</table>");
				}
				else if(i==spnsrList.size()-1)
					bf.append("</table>");
			}
		}
		
		return bf.toString();
	}
}
