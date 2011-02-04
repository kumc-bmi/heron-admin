package edu.ku.biostatistics.heron.util;

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
	/**
	 * check if a date string is valid
	 * @param aDate
	 * @return true if valid, false otherwise
	 */
	public boolean checkDateFormat(String aDate){
		String expression = "[01][0-2][/](0[1-9]|[12][0-9]|3[01])[/]\\d{4}"; 
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
				if(allIds[i]!=null){
					if(!ldapUtil.isUserInLdap(allIds[i])) {
						badIds.append(allIds[i]);
						badIds.append(" ");
					}
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
	 */
	public void sendEmails(String fromAddr, String toEmails, String subj, String contn,String host){
		try {
		      Properties props = new Properties();
		      props.put("mail.smtp.host", host);
		      Session mailConnection = Session.getInstance(props,  null);
		      Message msg = new MimeMessage(mailConnection);
		      Address[] addrs = InternetAddress.parse(toEmails);
		      msg.setContent(contn, "text/plain");
		      msg.setFrom(new InternetAddress(fromAddr));
		      msg.setRecipients(Message.RecipientType.TO, addrs);
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
	public void sendNotificationEmailToDroc(String toEmails){
		String subj = "HERON Sponsorship needs your attention";
		String contn = "Dear HERON DROC member,\n \n "+
			"HERON request has been submitted which may need your approval. \n \n" +
			"Thanks. \n \n"+
			"HERON Team.";
		this.sendEmails("heron-admin@kumc.edu", toEmails, subj, contn, "smtp.kumc.edu");
	}
}
