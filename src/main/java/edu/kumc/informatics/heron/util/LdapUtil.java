/**
 * Utility to access ldap and grab info.
 * 
 * Dongsheng Zhu
 */
package edu.kumc.informatics.heron.util;

import java.util.Hashtable;
import java.util.Properties;

import javax.naming.Context;
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
	protected static Log log = LogFactory.getLog(LdapUtil.class);  // TODO: invert control
	private static StaticDataUtil props = StaticDataUtil.getSoleInstance(); // todo: invert control

        /**
         *
         * @param props
         * @return
         * @throws NamingException
         *
         * beware of:
         * Caused by: javax.net.ssl.SSLHandshakeException: sun.security.validator.ValidatorException: PKIX path building failed: sun.security.provider.certpath.SunCertPathBuilderException: unable to find valid certification path to requested target
         * see http://code.google.com/p/java-use-examples/source/browse/trunk/src/com/aw/ad/util/InstallCert.java
         */
        private DirContext ldapContext(Properties props) throws NamingException  {
        	Hashtable<String,String> env = new Hashtable<String,String>();
		env.put(Context.INITIAL_CONTEXT_FACTORY,"com.sun.jndi.ldap.LdapCtxFactory");
		env.put(Context.PROVIDER_URL, props.getProperty(LDAP_PROV_URL));
		env.put(Context.SECURITY_AUTHENTICATION, "simple");
		env.put(Context.SECURITY_PROTOCOL, "ssl");
		env.put(Context.SECURITY_PRINCIPAL, props.getProperty(LDAP_PRINCIPAL));
		env.put(Context.SECURITY_CREDENTIALS, props.getProperty(LDAP_CREDENTIAL));
		DirContext ctx = null;

                return new InitialDirContext(env);
        }

        /**
         * TODO: throws NamingException
         * @param userId
         * @return
         */
        private NamingEnumeration searchUser(String userId) {
                try {
                        DirContext ctx = ldapContext(props.getProperties());
                        SearchControls controls = new SearchControls();
                        controls.setSearchScope(SearchControls.SUBTREE_SCOPE);
                        // TODO: scrub userId
                        return ctx.search("", "(cn=" + userId + ")", controls);
                } catch (NamingException e) {
                        throw new Error("searchUser failed", e);
                }
        }

	/**
	 * retrieve user info from ldap using userid/cn
	 * @param userId
	 * @return string[] of user info
         * TODO: consider the case of userId not found
	 */
        public String[] getUserInfo(String userId) {
                String[] info = new String[5];
                NamingEnumeration results = searchUser(userId);
                SearchResult searchResult;

                try {
                        if (results.hasMore()) {
                                searchResult = (SearchResult) results.next();
                                Attributes attributes = searchResult.getAttributes();
                                /*NamingEnumeration attrs = attributes.getAll();
                                while(attrs.hasMore()){
                                Attribute attr = (Attribute)attrs.next();
                                System.out.println(attr.toString());
                                }*/

                                String fname = (String) attributes.get("givenname").get();
                                String lname = (String) attributes.get("sn").get();
                                Attribute facAttr = attributes.get("kumcPersonFaculty");
                                String fac = facAttr != null ? (String) facAttr.get() : "";
                                Attribute attr = attributes.get("kumcPersonJobcode");
                                String jobCode = attr != null ? (String) attr.get() : null;
                                String title = (String) attributes.get("title").get();
                                Attribute emailAttr = attributes.get("mail");
                                String email = emailAttr != null ? (String) emailAttr.get() : "";
                                info[0] = fname + " " + lname;
                                info[1] = fac;
                                info[2] = title;
                                info[3] = jobCode;
                                info[4] = email;
                        }
                } catch (NamingException e) {
                        throw new Error("cannot get results", e);
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
                NamingEnumeration results = searchUser(userId);
                try {
                        return results.hasMore();
                } catch (NamingException e) {
                        throw new Error("cannot check for more results", e);
                }
	}
	
	/**
	 * retrieve ldap attribute value by name
	 * @param userId
	 * @param attr
	 * @return value of the attribute or "" if not found
	 */
        public String getLdapAttributeByName(String userId, String attr) {
                NamingEnumeration results = searchUser(userId);
                try {
                        if (results.hasMore()) {
                                SearchResult searchResult = (SearchResult) results.next();
                                Attributes attributes = searchResult.getAttributes();
                                return (String) attributes.get(attr).get();
                        }
                } catch (NamingException e) {
                        log.error("cannot get attribute", e);
                }
                return "";
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

        /* TODO: make this an automated test */
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