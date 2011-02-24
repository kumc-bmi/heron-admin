package edu.kumc.informatics.heron.util;

import static edu.kumc.informatics.heron.base.StaticValues.RAVEN_URL;

import java.util.Properties;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import javax.mail.Address;
import javax.mail.Message;
import javax.mail.Session;
import javax.mail.Transport;
import javax.mail.internet.InternetAddress;
import javax.mail.internet.MimeMessage;

/**
 * Basic utility class. put all basic utility functions here.
 * @author dongsheng zhu
 *
 */
public class BasicUtil {
	private LdapUtil ldapUtil = new LdapUtil();
	private Properties props = StaticDataUtil.getSoleInstance().getProperties();
	/**
	 * check if a date string is valid
	 * @param aDate
	 * @return true if valid, false otherwise
	 */
	public boolean checkDateFormat(String aDate){
		String expression = "(0[1-9]|1[0-2])[/](0[1-9]|[12][0-9]|3[01])[/]\\d{4}"; 
		Pattern p = Pattern.compile(expression);
	    Matcher m = p.matcher(aDate);
	    return m.matches();
	}
	
	/**
	 * check if any id in the ids string not valid.
	 * @param ids: id separated by ;
	 * @return the ids which not in ldap.
	 */
	public String ldapCheck(String ids){
		StringBuffer badIds = new StringBuffer("");
	
		if(ids!=null && !ids.trim().equals("")){
			String[] allIds = ids.split(";");
			for(int i=0; i<allIds.length;i++){
				if(allIds[i]!=null && !allIds[i].trim().equals("")){
					if(!ldapUtil.isUserInLdap(allIds[i].trim())) {
						badIds.append(allIds[i]);
						badIds.append(" ");
					}
				}
			}
		}
		return badIds.toString();
	}
	
	/**
	 * check if any id in the string[] not valid.
	 * @param allIds
	 * @return the ids which are not in ldap.
	 */
	public String ldapCheck(String[] allIds){
		StringBuffer badIds = new StringBuffer("");
	
		for(int i=0; i<allIds.length;i++){
			if(allIds[i]!=null && !allIds[i].trim().equals("")){
				if(!ldapUtil.isUserInLdap(allIds[i].trim())) {
					badIds.append(allIds[i]);
					badIds.append(" ");
				}
			}
		}
		return badIds.toString();
	}
	
	/**
	 * common method to send email
	 * @param fromAddr
	 * @param toEmails
	 * @param subj
	 * @param contn
	 * @param host
	 * @param ccEmails
	 */
	public void sendEmails(String fromAddr, String toEmails, String subj, String contn,String host,String ccEmails){
		try {
		      Properties props = new Properties();
		      props.put("mail.smtp.host", host);
		      Session mailConnection = Session.getInstance(props,  null);
		      Message msg = new MimeMessage(mailConnection);
		      Address[] addrs = InternetAddress.parse(toEmails);
		      Address[] ccAddrs = InternetAddress.parse(ccEmails);
		      msg.setContent(contn, "text/plain");
		      msg.setFrom(new InternetAddress(fromAddr));
		      msg.setRecipients(Message.RecipientType.TO, addrs);
		      msg.setRecipients(Message.RecipientType.CC,ccAddrs);
		      msg.setSubject(subj);
		      Transport.send(msg);  
		}
		catch (Exception ex) {
		      ex.printStackTrace(); 
		}
	}
	
	/**
	 * send email to droc team for heron approval
	 * @param toEmails
	 */
	public void sendNotificationEmailToDroc(String toEmails,String appUrl){
		String subj = "HERON Sponsorship needs your attention";
		String contn = "Dear HERON DROC member,\n \n "+
			"A HERON request has been submitted needs to be approved by your organization. \n \n" +
			"Please visit: \n\n" + appUrl +
			" and follow the \"Approve Sponsored HERON Users\" link \n\n"+
			"Sincerely, \n \n"+
			"The HERON Team.";
		this.sendEmails("heron-admin@kumc.edu", toEmails, subj, contn, "smtp.kumc.edu","");
	}
	
	/**
	 * send notification emails to User about sponsorship Approval Or Rejection
	 * @param userId
	 * @param sponsorId
	 * @param type
	 */
	public void notifyUserApprovedOrRejected(String userId,String sponsorId, String type,String proj){
		String[] userInfo = ldapUtil.getUserInfo(userId);
		String[] spnsrInfo = ldapUtil.getUserInfo(sponsorId);
		String subj = "HERON access request ";
		String contn = "Dear "+spnsrInfo[0]+",\n \n "+ "The HERON Data Request Oversight Committee has ";
		
		if(type.equals("A")){
			subj += "approved!";
			contn += "approved access for " + userInfo[0]+ " for project (" + proj+ "). " 
				+ "He/she will be required to sign a system access agreement if it has not been done so "
				+ "already for another project. He/she can login to  " + props.getProperty(RAVEN_URL)
				+ " and then access the HERON link on the left. If you have any questions, feel free to email heron-admin@kumc.edu.\n\n";
		}
		else{
			subj += "denied!";
			contn += "denied access for " + userInfo[0]+ " for project (" + proj+ ").\n\n" 
				+ "If you have any questions or want to voice concerns, please email heron-admin@kumc.edu and"
				+ " we will escalate your concerns to KUMC, UKP and KUH leadership. \n \n";
		}
		contn += "Sincerely, \n \n"+ "The HERON Team.";
		this.sendEmails("heron-admin@kumc.edu", spnsrInfo[4], subj, contn, "smtp.kumc.edu",userInfo[4]);
	}
}
