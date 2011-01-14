/**
 * Utility to access ldap and grab info.
 * 
 * Dongsheng Zhu
 */
package edu.ku.biostatistics.heron.util;

import java.util.Hashtable;
import java.util.Properties;

import javax.naming.Context;
import javax.naming.NameNotFoundException;
import javax.naming.NamingEnumeration;
import javax.naming.NamingException;
import javax.naming.directory.Attribute;
import javax.naming.directory.Attributes;
import javax.naming.directory.DirContext;
import javax.naming.directory.InitialDirContext;
import javax.naming.directory.SearchControls;
import javax.naming.directory.SearchResult;

import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;

import static edu.ku.biostatistics.heron.base.StaticValues.*;

public class LdapUtil {
	private static Hashtable<String,String> env = new Hashtable<String,String>();
	private static Properties props = StaticDataUtil.getSoleInstance().getProperties();
	private static Log log = LogFactory.getLog(LdapUtil.class);
	
	static {
		env.put(Context.INITIAL_CONTEXT_FACTORY,"com.sun.jndi.ldap.LdapCtxFactory");
		env.put(Context.PROVIDER_URL, props.getProperty(LDAP_PROV_URL));
		env.put(Context.SECURITY_AUTHENTICATION, "simple");
		env.put(Context.SECURITY_PROTOCOL, "ssl");
		env.put(Context.SECURITY_PRINCIPAL, props.getProperty(LDAP_PRINCIPAL));
		env.put(Context.SECURITY_CREDENTIALS, props.getProperty(LDAP_CREDENTIAL));
	}

	/**
	 * retrieve user info from ldap using userid/cn
	 * @param userId
	 * @return string[] of user info
	 */
	@SuppressWarnings("rawtypes")
	public String[] getUserInfo(String userId)
	{
		String[] info = new String[4];
		DirContext ctx = null;
		NamingEnumeration results = null;
		
		try {
			ctx = new InitialDirContext(env);
			SearchControls controls = new SearchControls();
			controls.setSearchScope(SearchControls.SUBTREE_SCOPE);
			results = ctx.search("", "(cn=" + userId + ")", controls);

			if (results.hasMore()) {
				SearchResult searchResult = (SearchResult) results.next();
				Attributes attributes = searchResult.getAttributes();
				NamingEnumeration attrs = attributes.getAll();
				while(attrs.hasMore()){
					Attribute attr = (Attribute)attrs.next();
					System.out.println(attr.toString());
				}
					
				String fname = (String) attributes.get("givenname").get();
				String lname = (String) attributes.get("sn").get();
				String fac = (String) attributes.get("kumcPersonFaculty").get();
				String jobCode = (String) attributes.get("kumcPersonJobCode").get();
				String title = (String) attributes.get("title").get();
				info[0] = fname + " " + lname;
				info[1] = fac;
				info[2] = title;
				info[3] = jobCode;
			}
		} catch (NameNotFoundException e) {
			log.error("NameNotFoundException in getUserInfo():"+e.getMessage());
		} catch (NamingException e) {
			log.error("NamingException in getUserInfo():"+e.getMessage());
		} catch(Exception e){
			log.error("Other exception in getUserInfo():"+e.getMessage());
		}finally {
			if (results != null) {
				try {
					results.close();
				} catch (Exception e) {
					// Never mind this.
				}
			}
			if (ctx != null) {
				try {
					ctx.close();
				} catch (Exception e) {
					// Never mind this.
				}
			}
		}
		return info;
	}
	
	/**
	 * check if a user is in ldap
	 * @param userId
	 * @return true if yet in ldap
	 */
	public boolean isUserInLdap(String userId)
	{
		DirContext ctx = null;
		@SuppressWarnings("rawtypes")
		NamingEnumeration results = null;
		boolean found = false;
		try {
			ctx = new InitialDirContext(env);
			SearchControls controls = new SearchControls();
			controls.setSearchScope(SearchControls.SUBTREE_SCOPE);
			results = ctx.search("", "(cn=" + userId + ")", controls);
			found = results.hasMore();
		} catch (NameNotFoundException e) {
			log.error("NameNotFoundException in getUserInfo():"+e.getMessage());
		} catch (NamingException e) {
			log.error("NamingException in getUserInfo():"+e.getMessage());
		} catch(Exception e){
			log.error("Other exception in getUserInfo():"+e.getMessage());
		}finally {
			if (results != null) {
				try {
					results.close();
				} catch (Exception e) {
					// Never mind this.
				}
			}
			if (ctx != null) {
				try {
					ctx.close();
				} catch (Exception e) {
					// Never mind this.
				}
			}
		}
		return found;
	}

	public static void main(String[] args) {
		new LdapUtil().getUserInfo("dzhu");
	}
}