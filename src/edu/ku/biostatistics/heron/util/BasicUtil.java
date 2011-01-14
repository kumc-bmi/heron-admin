package edu.ku.biostatistics.heron.util;

import java.util.regex.Matcher;
import java.util.regex.Pattern;

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
}
