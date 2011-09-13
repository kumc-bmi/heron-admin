/* Copyright (c) 2011 The University of Kansas Medical Center
 * http://informatics.kumc.edu/ */

package edu.kumc.informatics.heron.capsec;

import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import javax.naming.NameNotFoundException;
import javax.naming.NoPermissionException;
import javax.naming.directory.Attributes;
import javax.naming.directory.BasicAttributes;
import javax.naming.directory.DirContext;
import javax.servlet.ServletException;
import javax.servlet.http.HttpServletRequest;
import javax.xml.xpath.XPath;
import javax.xml.xpath.XPathExpressionException;
import javax.xml.xpath.XPathFactory;

import org.w3c.dom.Node;
import org.xml.sax.InputSource;

import org.jasig.cas.client.authentication.AttributePrincipal;
import org.jasig.cas.client.util.AbstractCasFilter;
import org.jasig.cas.client.validation.Assertion;
import org.junit.Test;
import org.junit.Assert;

import org.springframework.ldap.NamingException;
import org.springframework.ldap.core.ContextSource;
import org.springframework.ldap.core.LdapTemplate;

import edu.kumc.informatics.heron.dao.ChalkDao;
import edu.kumc.informatics.heron.util.HCardContext;
import org.springframework.mock.web.MockHttpServletRequest;

public class LDAPEnterpriseTest {
	public static final String mockData = "/mockDirectory.html";

	public LDAPEnterprise mockMedCenter() {
		InputSource xmlsrc = new InputSource(getClass().getResourceAsStream(mockData));
		KUMCHCardContext pplinfo;
                try {
	                pplinfo = new KUMCHCardContext(xmlsrc);
                } catch (XPathExpressionException e) {
	                throw new IllegalArgumentException(e);
                }
		LdapTemplate cardsTemplate = new LdapTemplate(new KUMCHCardSource(pplinfo));
		return new LDAPEnterprise(cardsTemplate, pplinfo);
	}

	@Test
	public void parseSomething() throws XPathExpressionException {
		XPath xpath = XPathFactory.newInstance().newXPath();
		InputSource src = new InputSource(getClass().getResourceAsStream(mockData));
		Assert.assertNotNull(xpath.evaluate("/html/head/title", src));
	}


	@Test
	public void findKnownAgent() throws NameNotFoundException {
		Agent js = mockMedCenter().affiliate("john.smith");
		Assert.assertEquals("John Smith", js.getFullName());
		Assert.assertEquals("Chair of Department of Neurology", js.getTitle());
	}

	@Test
	public void goodAgentToString() throws NameNotFoundException {
		Agent js = mockMedCenter().affiliate("john.smith");
		Assert.assertTrue(js.toString().contains(js.getUserId()));
	}

	@Test(expected = NameNotFoundException.class)
	public void dontFindUnknownAgent() throws NameNotFoundException {
		mockMedCenter().affiliate("nobody.we.know");
	}

	@Test
	public void findFaculty() throws NoPermissionException, ServletException {
		LDAPEnterprise e = mockMedCenter();
		Agent fac = e.affiliate(mockCASRequest("john.smith"));
		Assert.assertEquals("John Smith", fac.getFullName());
	}

	@Test(expected = NoPermissionException.class)
	public void studentNotFaculty() throws NoPermissionException,
			ServletException {
		LDAPEnterprise e = mockMedCenter();
		Agent bill = e.affiliate(mockCASRequest("bill.student"));
		e.checkFaculty(bill);
	}

	//HCardContext doesn't support this sort of search yet.
	public void findSomePeople() throws NoPermissionException,
			ServletException {
		LDAPEnterprise e = mockMedCenter();
		List<? extends Agent> hits = e.affiliateSearch("Smith", "", "");
		Assert.assertTrue(hits.size() == 1);
	}

	public static HttpServletRequest mockCASRequest(String userid) {
		MockHttpServletRequest q = new MockHttpServletRequest("GET", "/");
		Assertion a = new MockAssertion(userid);
		q.getSession(true).setAttribute(AbstractCasFilter.CONST_CAS_ASSERTION,
				a);
		return q;
	}

	private static class MockAssertion implements Assertion {
		private static final long serialVersionUID = 1L;

		private final MockPrincipal _who;

		public MockAssertion(String name) {
			_who = new MockPrincipal(name);
		}

		@Override
		public Map<String, Object> getAttributes() {
			// TODO Auto-generated method stub
			return null;
		}

		@Override
		public AttributePrincipal getPrincipal() {
			return _who;
		}

		@Override
		public Date getValidFromDate() {
			// TODO Auto-generated method stub
			return null;
		}

		@Override
		public Date getValidUntilDate() {
			// TODO Auto-generated method stub
			return null;
		}

	}

	private static class MockPrincipal implements AttributePrincipal {
		private static final long serialVersionUID = 1L;
		private final String _name;

		public MockPrincipal(String name) {
			_name = name;
		}

		@Override
		public Map<String, Object> getAttributes() {
			return new HashMap<String, Object>();
		}

		@Override
		public String getProxyTicketFor(String arg0) {
			throw new UnsupportedOperationException();
		}

		@Override
		public String getName() {
			return _name;
		}

	}

	public static class KUMCHCardContext extends HCardContext implements ChalkDao {
		public KUMCHCardContext(InputSource hCardSrc) throws XPathExpressionException {
			super(hCardSrc);
		}

		private static final Map<String, String> ldap2hcard = new HashMap<String, String>() {
			private static final long serialVersionUID = 1L;

			{
				put("sn", "family-name");
				put("givenname", "given-name");
				put("title", "title");
				put("mail", "email");
				put("kumcPersonFaculty", "kumcPersonFaculty");
				put("kumcPersonJobcode", "kumcPersonJobcode");
			}
		};

		public Attributes cardAttributes(Node hcard) {
			BasicAttributes out = new BasicAttributes();
			for (String ldapattr : ldap2hcard.keySet()) {
				String hcardClass = ldap2hcard.get(ldapattr);
				out.put(ldapattr, getHCardProperty(hcard, hcardClass));
			}
			return out;
		}

		@Override
                public Date getChalkTrainingExpireDate(Agent who) {
			String dtend;
			dtend = getHCardProperty(findCards(who.getUserId()).item(0), "dtend");
			SimpleDateFormat iso = new SimpleDateFormat("yyyy-mm-dd");
			try {
	                        return iso.parse(dtend);
                        } catch (ParseException e) {
	                        return null;
                        }
		}
	}

	/**
	 * Spring ContextSource to build a KUMCHCardContext
	 */
	protected static class KUMCHCardSource implements ContextSource {
		public KUMCHCardSource(KUMCHCardContext ctx) {
			_ctx = ctx;
		}
		private final KUMCHCardContext _ctx;
		
		@Override
		public DirContext getReadOnlyContext() throws NamingException {
			return _ctx;
		}

		@Override
		public DirContext getReadWriteContext() throws NamingException {
			throw new UnsupportedOperationException("Not supported yet.");
		}

		/**
		 * I'm not sure this is faithful to the interface...
		 * 
		 * @param u
		 * @param p
		 * @return
		 * @throws NamingException
		 */
		@Override
		public DirContext getContext(String u, String p) throws NamingException {
			return getReadOnlyContext();
		}
	}
}