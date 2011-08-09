/* Copyright (c) 2010-2011 The University of Kansas Medical Center
 * http://informatics.kumc.edu/
 */
package edu.kumc.informatics.heron.util;


import javax.mail.MessagingException;
import javax.mail.Message;

import static org.junit.Assert.*;

	import org.junit.Test;
import org.junit.runner.RunWith;
import org.springframework.test.annotation.IfProfileValue;
import org.springframework.test.context.junit4.SpringJUnit4ClassRunner;

        /**
         * TODO: factor out dependency on real LDAP service. integration test?
         * @author dzhu, dconnolly
         */
@IfProfileValue(name="test-groups", values={"integration-tests"})
@RunWith(SpringJUnit4ClassRunner.class)
	public class LdapUtilTest extends LdapUtil{
		@Test
		public void testGetDrocEmails() throws MessagingException{
                        String addr1 = this.getDrocEmails(new String[]{"rwaitman"});
			assertTrue(addr1.length() > 0);

                        String addrN = this.getDrocEmails(new String[]{"rwaitman", "kblackwe",
                        "rbarohn", "tneely", "lwood2", "jorndoff", "cwittkop",
                        "trusconi", "cgardner", "kgrasso", });
			assertTrue(addrN.length() > 0);

                        /* TODO: use Spring Mail instead
                        Mailer mailer = new Mailer("smtp.kumc.edu"); // TODO:@@

                        Message msg1 = mailer.render("a droc notification", "dconnolly+test@kumc.edu",
                                "dconnolly@kumc.edu,dconnolly@kumc.edu", "",
                                "Dear DROC members, ...");
                        mailer.send(msg1);

                        Message msg0 = mailer.render("a droc notification with extra comma", "dconnolly+test@kumc.edu",
                                "dconnolly@kumc.edu,dconnolly@kumc.edu,", "",
                                "Dear DROC members, ...");
                        mailer.send(msg0);
*/

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