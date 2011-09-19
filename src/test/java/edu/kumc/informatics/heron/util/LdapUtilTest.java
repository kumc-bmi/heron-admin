
	package edu.kumc.informatics.heron.util;

	import static org.junit.Assert.*;

	import org.junit.Test;

        /**
         * TODO: factor out dependency on real LDAP service. integration test?
         * @author dzhu, dconnolly
         */
	public class LdapUtilTest extends LdapUtil{
		@Test
		public void testGetDrocEmails(){
		    //assertTrue(this.getDrocEmails(new String[]{"rwaitman"}).length()>0);
		}
		
		@Test
		public void testGetLdapAttributeByName(){
		    //assertTrue(this.getLdapAttributeByName("rwaitman", "mail").length()>0);
		}
		
		@Test
		public void testIsUserInLdap(){
		    //assertTrue(this.isUserInLdap("rwaitman"));
		}
	}