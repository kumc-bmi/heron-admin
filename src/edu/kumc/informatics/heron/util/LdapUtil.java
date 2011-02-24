/**
 * Utility to access ldap and grab info.
 * 
 * Dongsheng Zhu
 */
package edu.kumc.informatics.heron.util;

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

import static edu.kumc.informatics.heron.base.StaticValues.*;

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
		String[] info = new String[5];
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
				/*NamingEnumeration attrs = attributes.getAll();
				while(attrs.hasMore()){
					Attribute attr = (Attribute)attrs.next();
					System.out.println(attr.toString());
				}*/
					
				String fname = (String) attributes.get("givenname").get();
				String lname = (String) attributes.get("sn").get();
				Attribute facAttr = attributes.get("kumcPersonFaculty");
				String fac = facAttr!=null?(String)facAttr.get():"";
				Attribute attr = attributes.get("kumcPersonJobcode");
				String jobCode = attr!=null?(String) attr.get():null;
				String title = (String) attributes.get("title").get();
				Attribute emailAttr = attributes.get("mail");
				String email = emailAttr!=null?(String)emailAttr.get():"";
				info[0] = fname + " " + lname;
				info[1] = fac;
				info[2] = title;
				info[3] = jobCode;
				info[4] = email;
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
	 * @return true if yes in ldap
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
	
	/**
	 * retrieve ldap attribute value by name
	 * @param userId
	 * @param attr
	 * @return value of the attribute
	 */
	public String getLdapAttributeByName(String userId, String attr){
		DirContext ctx = null;
		NamingEnumeration results = null;
		String attrValue = "";
		try {
			ctx = new InitialDirContext(env);
			SearchControls controls = new SearchControls();
			controls.setSearchScope(SearchControls.SUBTREE_SCOPE);
			results = ctx.search("", "(cn=" + userId + ")", controls);

			if (results.hasMore()) {
				SearchResult searchResult = (SearchResult) results.next();
				Attributes attributes = searchResult.getAttributes();
				attrValue = (String) attributes.get(attr).get();
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
		return attrValue;
	
	}
	
	/**
	 * get emails of the droc
	 * @param ids
	 * @return emails separated by ,
	 */
	public String getDrocEmails(String[] ids){
		StringBuffer bf = new StringBuffer();
		
		for(String id : ids){
			bf.append(getLdapAttributeByName(id,"mail"));
			bf.append(",");
		}
		return bf.toString();
	}
	
	/*public static void main(String[] args) {
		LdapUtil util = new LdapUtil();
		String[] uids = new String[]{"cowens","dzhu", "rwaitman", "dconnolly","mmayo","msmith11","kblackwe","rbarohn","tneely","jorndoff","cwittkop","trusconi"};
		
		for(String uid:uids){
			System.out.println(uid+ ": ou:"+ util.getLdapAttributeByName(uid,"ou")+", org:" 
				+ util.getLdapAttributeByName(uid,"kumcPersonEntity") + ", title:"
				+ util.getLdapAttributeByName(uid,"title")) ;
		}
	}*/
}