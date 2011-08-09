/*
 * To change this template, choose Tools | Templates
 * and open the template in the editor.
 */
package edu.kumc.informatics.heron.servlet;

import java.util.Arrays;
import java.util.LinkedList;
import java.util.ArrayList;
import java.util.List;
import javax.servlet.http.HttpServletRequest;
import org.junit.Test;
import org.junit.Assert;
import org.junit.runner.RunWith;
import org.springframework.test.AbstractTransactionalDataSourceSpringContextTests;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.SpringJUnit4ClassRunner;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockServletContext;
import edu.kumc.informatics.heron.util.Functional;

/**
 *
 * @author dconnolly
 */
// @RunWith(SpringJUnit4ClassRunner.class)
//get rid of this? @ContextConfiguration(locations={"classpath:heron-integration-context.xml"})
public class SponsorshipServletTest  {

        @Test
        public void parsingATrivialDescription() {
                Functional.Pair<ArrayList<String>, ArrayList<String>> actual =
                        SponsorshipServlet.Input.parseNonEmployees("bob");
                Assert.assertEquals(1, actual.getLeft().size());
                Assert.assertEquals("bob", actual.getLeft().get(0));
                Assert.assertEquals(null, actual.getRight().get(0));
        }

        @Test
        public void parsingAnInterestingDescription() {
                Functional.Pair<ArrayList<String>, ArrayList<String>> actual =
                        SponsorshipServlet.Input.parseNonEmployees(
                        "bob; scooby [my favorite dog]; jane");
                Assert.assertEquals(3, actual.getLeft().size());
                Assert.assertEquals("my favorite dog", actual.getRight().get(1));
        }

        @Test(expected= IllegalArgumentException.class)
        public void rejectingDescriptionsWithGoofyFormat() {
                Functional.Pair<ArrayList<String>, ArrayList<String>> actual =
                        SponsorshipServlet.Input.parseNonEmployees(
                        "bob; sue[bad;format]; joe");
        }

        @Test(expected= IllegalArgumentException.class)
        public void rejectingAnotherGoofyFormat() {
                Functional.Pair<ArrayList<String>, ArrayList<String>> actual =
                        SponsorshipServlet.Input.parseNonEmployees(
                        "; ;; []");
        }

        @Test
        public void validatingInput() {
                MockHttpServletRequest q = new MockHttpServletRequest(new MockServletContext(), "GET", "/");
                q.addParameter(SponsorshipServlet.Form.TITLE, "cure cancer");
                q.addParameter(SponsorshipServlet.Form.DESC, "great stuff");
                q.addParameter(SponsorshipServlet.Form.EMPIDS, "dconnolly");
                q.addParameter(SponsorshipServlet.Form.NONEMPIDS, ""); // todo: test empty
                q.addParameter(SponsorshipServlet.Form.SPONSOR_TYPE, "");
                SponsorshipServlet.Input subject = new SponsorshipServlet.Input(q);
                Assert.assertEquals("", subject.messages());
        }

        /* @@TODO: ldap testing
	@Test
	public void findingAllUsersInLDAP(){
                Assert.assertEquals("", testLdapValidate(Functional.cons("rwaitman", new LinkedList<String>())));
	}

	@Test
	public void findingSomeUsersInLDAP(){
                Assert.assertEquals("lose: tester. ", testLdapValidate(Arrays.asList("rwaitman","tester")));
	}

        private String testLdapValidate(List<String> names) {
                T subject = new T();
                subject.init();
                StringBuilder buf = new StringBuilder();
                LdapUtil ldapUtil = new LdapUtil();
		subject.testLdapValidate(names, ldapUtil, buf, "lose: ");
                return buf.toString();
        }
         
         */
}
