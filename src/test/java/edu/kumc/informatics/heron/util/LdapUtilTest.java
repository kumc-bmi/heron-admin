
	package edu.kumc.informatics.heron.util;

	import static org.junit.Assert.*;

	import org.junit.Test;

	public class LdapUtilTest extends LdapUtil{
		@Test
		public void testGetDrocEmails(){
			assertTrue(this.getDrocEmails(new String[]{"rwaitman"}).length()>0);
		}
		
		@Test
		public void testGetLdapAttributeByName(){
			assertTrue(this.getLdapAttributeByName("rwaitman", "mail").length()>0);
		}
		
		@Test
		public void testIsUserInLdap(){
			assertTrue(this.isUserInLdap("rwaitman"));
		}
	}