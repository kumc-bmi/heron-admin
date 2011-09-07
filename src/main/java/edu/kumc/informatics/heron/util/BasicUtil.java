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
@Deprecated
public class BasicUtil {
	private LdapUtil ldapUtil = new LdapUtil();
	private Properties props = StaticDataUtil.getSoleInstance().getProperties();
	/**
	 * check if a date string is valid
	 * @param aDate
	 * @return true if valid, false otherwise
         * @deprecated in favor of java.text.SimpleDateFormat
	 */
        @Deprecated
	public boolean checkDateFormat(String aDate){
		String expression = "(0[1-9]|1[0-2])[/](0[1-9]|[12][0-9]|3[01])[/]\\d{4}"; 
		Pattern p = Pattern.compile(expression);
	    Matcher m = p.matcher(aDate);
	    return m.matches();
	}
}
