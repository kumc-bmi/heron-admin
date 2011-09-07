/* Copyright (c) 2011 The University of Kansas Medical Center
 * http://informatics.kumc.edu/ */
package edu.kumc.informatics.heron.servlet;

import java.security.acl.NotOwnerException;
import java.util.Arrays;
import java.util.Collection;
import java.util.Date;
import java.util.GregorianCalendar;

import javax.naming.NoPermissionException;
import javax.servlet.ServletException;
import javax.servlet.http.HttpServletRequest;

import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;
import org.junit.Assert;
import org.junit.Test;
import org.springframework.mock.web.MockHttpServletResponse;
import org.springframework.web.servlet.ModelAndView;

import edu.kumc.informatics.heron.capsec.AcademicMedicalCenter;
import edu.kumc.informatics.heron.capsec.Agent;
import edu.kumc.informatics.heron.capsec.LDAPEnterpriseTest;
import edu.kumc.informatics.heron.capsec.RepositoryUser;
import edu.kumc.informatics.heron.capsec.Sponsor;
import edu.kumc.informatics.heron.capsec.SystemAccessRecords;
import edu.kumc.informatics.heron.servlet.MyChecklist.ChecklistProperty;

/**
 * TODO: add chalk, no chalk tests
 * @author dconnolly
 */
public class MyChecklistTest {
	MockHttpServletResponse aResponse = new MockHttpServletResponse();
	AcademicMedicalCenter org = new LDAPEnterpriseTest().mockMedCenter();
	SystemAccessRecords sar = new MockRecords(org, "john.smith,mary.jones", 2011, 8);
	MyChecklist controller = new MyChecklist(org, sar);
	
	@Test
	public void studentChecklistHasName() throws Exception {
		HttpServletRequest q = LDAPEnterpriseTest.mockCASRequest("bill.student");

		ModelAndView modelAndView = controller.handleRequest(q, aResponse);
		Assert.assertEquals(MyChecklist.VIEW_NAME, modelAndView.getViewName());
		Assert.assertNotNull(modelAndView.getModel());

		Agent who = new ModelProperty<Agent>(modelAndView, ChecklistProperty.AFFILIATE).value();
		Assert.assertEquals("Bill Student", who.getFullName());
		Assert.assertEquals(null,
		                new ModelProperty<String>(modelAndView, ChecklistProperty.REPOSITORY_TOOL).value());
		Assert.assertEquals(null,
		                new ModelProperty<String>(modelAndView, ChecklistProperty.SPONSORSHIP_FORM).value());
	}

	/**
	 * Use ChecklistProperty rather than String to access a property.
	 * @author dconnolly
	 *
	 * @param <T> value type of the property
	 */
	private class ModelProperty <T> {
		@SuppressWarnings("unchecked")
		ModelProperty(ModelAndView mav, ChecklistProperty p) {
			try {
				_value = (T) mav.getModel().get(p.toString());
			} catch (ClassCastException ex) {
				throw new IllegalArgumentException(ex);
			}
		}
		private T _value;
		
		T value() {
			return _value;
		}
    }

    @Test
    public void facChecklistHasAll() throws Exception{
    	HttpServletRequest q = LDAPEnterpriseTest.mockCASRequest("john.smith");

        ModelAndView modelAndView = controller.handleRequest(q, aResponse);
        Assert.assertEquals(MyChecklist.VIEW_NAME, modelAndView.getViewName());
        Assert.assertNotNull(modelAndView.getModel());
        Agent who = new ModelProperty<Agent>(modelAndView, MyChecklist.ChecklistProperty.AFFILIATE).value();
        Assert.assertEquals("John Smith", who.getFullName());
        Assert.assertEquals("Chair of Department of Neurology", who.getTitle());
        Assert.assertEquals(Boolean.FALSE, new ModelProperty<String>(modelAndView, ChecklistProperty.TRAINING_EXPIRED).value());
        Assert.assertNotNull(new ModelProperty<String>(modelAndView, ChecklistProperty.REPOSITORY_TOOL).value());
        Assert.assertNotNull(new ModelProperty<String>(modelAndView, ChecklistProperty.SPONSORSHIP_FORM).value());
    }
    
    static class MockRecords implements SystemAccessRecords {
    	final Log logger = LogFactory.getLog(getClass());
    	final AcademicMedicalCenter _org;
    	final Collection<String> _names;
    	final Date today;
    	
    	/**
    	 * Make a SystemAccessRecords where the given names have signed the access agreement.
    	 * @param org
    	 * @param names comma separated
    	 */
    	public MockRecords(AcademicMedicalCenter org, String names, int year, int month) {
    		_org = org;
    		_names = Arrays.asList(names.split(","));
    		GregorianCalendar c = new GregorianCalendar();
    		c.set(year, month, 1);
    		today = c.getTime();
    	}
    	
		private static class Ready implements Qualification {
			public Ready(Agent a) {
				_who = a;
			}
			Agent _who;
			@Override
                        public Agent forWhom() {
	                        return _who;
                        }
			
		}
		@Override
                public Qualification facultyUser(HttpServletRequest q) throws NoPermissionException, ServletException {
	                Agent a = _org.affiliate(q);
	                _org.checkFaculty(a);
	                return new Ready(a);
                }

		@Override
                public Qualification sponsoredUser(HttpServletRequest q) throws NoPermissionException, ServletException {
			throw this.notSponsored; // TODO
                }

		@Override
                public Qualification executiveUser(HttpServletRequest q) throws NoPermissionException, ServletException {
	                throw this.notExecutive; // TODO
                }

		@Override
		// TODO: factor to abstract class?
                public Qualification qualifiedUser(HttpServletRequest q) throws NoPermissionException, ServletException {
			try {
				return executiveUser(q);
			} catch (NoPermissionException notexec) {
				try {
					return facultyUser(q);
				} catch (NoPermissionException notfac){
					return sponsoredUser(q);
				}
			}
		}

		@Override
                public RepositoryUser repositoryUser(Qualification q) throws NoPermissionException {
			Agent a = q.forWhom();
			if (!_names.contains(a.getUserId())) {
				logger.info("not in list: [" + a.getUserId() + "] list:" + _names.toString());
				throw nosig;
			}
			
			return new MockUser(a, checkTraining(a));
                }


		@Override
                public Sponsor asSponsor(HttpServletRequest q) throws NoPermissionException, ServletException {
			Agent who = _org.affiliate(q);
			_org.checkFaculty(who);
			checkTraining(who);
			
			// TODO: check chalk, sig
			if (!_names.contains(who.getUserId())) {
				logger.info("not in list: [" + who.getUserId() + "] list:" + _names.toString());
				throw new NoPermissionException();
			}
			return new MockSponsor();
                }

		private Date checkTraining(Agent who) throws NoPermissionException {
			Date exp = _org.trainedThru(who);
	                if (today.after(exp)) {
				throw trainingOutOfDate;
			}
	                return exp;
                }
    	
    }

    static class MockUser implements RepositoryUser {
            final Agent _who;
            final Date _exp;
            MockUser(Agent who, Date exp) {
                    _who = who;
                    _exp = exp;
            }
		@Override
		public String getFullName() {
			return _who.getFullName();
		}

		@Override
		public String getTitle() {
			return _who.getTitle();
		}
		
		@Override
		public String getMail() {
			return _who.getMail();
		}
                @Override
                public String getUserId() {
                        return _who.getUserId();
                }
                @Override
                public Date getHSCTrainingExpiration() {
                        return _exp;
                }
                @Override
                public boolean acknowledgedRecentDisclaimers() {
                        return false; // TODO test this
                }
                @Override
                public void acknowledgeRecentDisclaimers() {
                        throw new RuntimeException(); // TODO Auto-generated method stub                        
                }
    	
    }

    static class MockSponsor implements Sponsor {

		@Override
		public void fileRequest(String title, Agent who)
				throws NotOwnerException {
			throw new UnsupportedOperationException("mock sponsor cannot file requests.");			
		}
    }
}
