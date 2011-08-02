/* Copyright (c) 2011 The University of Kansas Medical Center
 * http://informatics.kumc.edu/ */

package edu.kumc.informatics.heron.util;

import edu.kumc.informatics.heron.capsec.Agent;
import edu.kumc.informatics.heron.capsec.Enterprise;
import edu.kumc.informatics.heron.capsec.Ticket;
import javax.naming.NamingException;
import javax.servlet.ServletException;
import javax.servlet.http.HttpServletRequest;
import org.junit.Test;
import org.junit.Assert;
import org.junit.runner.RunWith;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.SpringJUnit4ClassRunner;
import org.springframework.ldap.core.LdapTemplate;
import org.springframework.mock.web.MockHttpServletRequest;


@RunWith(SpringJUnit4ClassRunner.class)
@ContextConfiguration(locations={"classpath:ldap-context.xml"})
public class EnterpriseAuthorityTest {

        @Autowired
        LdapTemplate t;

        @Test
        /**
         * TODO: use mock LDAP data and service
         */
        public void lookSomebodyUp() throws NamingException, ServletException {
                MockHttpServletRequest q = new MockHttpServletRequest("GET", "/");
                MockCASCheck cas_check = new MockCASCheck();
                MockEnterprise e = new MockEnterprise(t);
                Agent who = e.affiliate(cas_check.getName());
                Assert.assertEquals("Dan Connolly", who.getFullName());
                Assert.assertEquals("dconnolly@kumc.edu", who.getMail());
        }

        static class MockEnterprise extends Enterprise {
                public MockEnterprise(LdapTemplate t) {
                        super(t);
                }
        }

        static class MockCASCheck implements Ticket {
                public String getName() {
                        return "dconnolly";
                }
        }
}

