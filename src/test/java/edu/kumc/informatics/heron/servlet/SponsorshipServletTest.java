/*
 * To change this template, choose Tools | Templates
 * and open the template in the editor.
 */

package edu.kumc.informatics.heron.servlet;

import java.util.List;
import junit.framework.TestCase;
import org.junit.Test;
import org.junit.Assert;

/**
 *
 * @author dconnolly
 */
public class SponsorshipServletTest {
        static class T extends SponsorshipServlet {
                public List<SponsorshipServlet.Pair<String, String>> parts(
                        String text) {
                        return parseNonEmployees(text);
                }
        }

        @Test
        public void parsingATrivialDescription() {
                T subject = new T();
                List<SponsorshipServlet.Pair<String, String>> actual = subject.parts("bob");
                Assert.assertEquals(1, actual.size());
                Assert.assertEquals("bob", actual.get(0).getLeft());
                Assert.assertEquals(null, actual.get(0).getRight());
        }

        @Test
        public void parsingAnInterestingDescription() {
                T subject = new T();
                List<SponsorshipServlet.Pair<String, String>> actual = subject.parts(
                        "bob; scooby [my favorite dog]; jane");
                Assert.assertEquals(3, actual.size());
                Assert.assertEquals("my favorite dog", actual.get(1).getRight());
        }

        @Test(expected= IllegalArgumentException.class)
        public void rejectingDescriptionsWithNoNames() {
                T subject = new T();
                List<SponsorshipServlet.Pair<String, String>> actual = subject.parts(
                        ";; ;; ; ");
        }

        @Test(expected= IllegalArgumentException.class)
        public void rejectingDescriptionsWithGoofyFormat() {
                T subject = new T();
                List<SponsorshipServlet.Pair<String, String>> actual = subject.parts(
                        "bob; sue[bad;format]; joe");
        }
}
