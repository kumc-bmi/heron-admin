/* Copyright (c) 2011 The University of Kansas Medical Center
 * http://informatics.kumc.edu/ */
package edu.kumc.informatics.heron.servlet;

import java.security.acl.NotOwnerException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collection;
import java.util.Date;
import java.util.List;

import javax.naming.NameNotFoundException;
import javax.naming.NoPermissionException;
import javax.servlet.ServletException;
import javax.servlet.http.HttpServletRequest;

import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;
import org.junit.Test;
import org.junit.Assert;
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
	AcademicMedicalCenter org = LDAPEnterpriseTest.mockMedCenter();
	SystemAccessRecords sar = new MockRecords(org, "john.smith,mary.jones");
	MyChecklist controller = new MyChecklist(org, sar);
	
	@Test
    public void studentChecklistHasName() throws Exception{
    	HttpServletRequest q = LDAPEnterpriseTest.mockCASRequest("bill.student");
    	
        ModelAndView modelAndView = controller.handleRequest(q, aResponse);
        Assert.assertEquals(MyChecklist.VIEW_NAME, modelAndView.getViewName());
        Assert.assertNotNull(modelAndView.getModel());
        
        Agent who = new ModelProperty<Agent>(modelAndView, ChecklistProperty.AFFILIATE).value();
        Assert.assertEquals("Bill Student", who.getFullName());
        Assert.assertEquals(null, new ModelProperty<String>(modelAndView, ChecklistProperty.REPOSITORY_TOOL).value());
        Assert.assertEquals(null, new ModelProperty<String>(modelAndView, ChecklistProperty.SPONSORSHIP_FORM).value());
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
        Assert.assertNotNull(new ModelProperty<String>(modelAndView, ChecklistProperty.REPOSITORY_TOOL).value());
        Assert.assertNotNull(new ModelProperty<String>(modelAndView, ChecklistProperty.SPONSORSHIP_FORM).value());
    }
    
    static class MockRecords implements SystemAccessRecords {
    	final Log logger = LogFactory.getLog(getClass());
    	final AcademicMedicalCenter _org;
    	final Collection<String> _names;
    	
    	/**
    	 * Make a SystemAccessRecords where the given names have signed the access agreement.
    	 * @param org
    	 * @param names comma separated
    	 */
		public MockRecords(AcademicMedicalCenter org, String names) {
    		_org = org;
    		_names = Arrays.asList(names.split(","));
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
	                // TODO Auto-generated method stub
	                return null;
                }

		@Override
                public Qualification sponsoredUser(HttpServletRequest q) throws NoPermissionException, ServletException {
	                // TODO Auto-generated method stub
	                return null;
                }

		@Override
                public Qualification executiveUser(HttpServletRequest q) throws NoPermissionException, ServletException {
	                // TODO Auto-generated method stub
	                return null;
                }

		@Override
                public Qualification qualifiedUser(HttpServletRequest q) throws NoPermissionException, ServletException {
	                // TODO Auto-generated method stub
	                return null;
                }

		@Override
                public RepositoryUser repositoryUser(Agent a, Qualification q) throws NoPermissionException {
			Agent agt;
                        try {
	                        agt = _org.affiliate(a.getUserId());
                        } catch (NameNotFoundException e) {
	                        // TODO Auto-generated catch block
	                        e.printStackTrace();
                        }
			if (!_names.contains(a.getUserId())) {
				logger.info("not in list: [" + a.getUserId() + "] list:" + _names.toString());
				throw new NoPermissionException();
			}
			
			// TODO: check training
			
			return new MockUser(a);
                }


		@Override
                public Sponsor asSponsor(HttpServletRequest q) throws NoPermissionException, ServletException {
			Agent who = _org.affiliate(q);
			_org.withFaculty(who, null); //TODO: !!!
			// TODO: check chalk, sig
			if (!_names.contains(who.getUserId())) {
				logger.info("not in list: [" + who.getUserId() + "] list:" + _names.toString());
				throw new NoPermissionException();
			}
			return new MockSponsor();
                }
    	
    }

    static class MockUser implements RepositoryUser {
            final Agent _who;
            MockUser(Agent who) {
                    _who = who;
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
                        throw new RuntimeException(); // TODO Auto-generated method stub
                }
                @Override
                public boolean acknowledgedRecentDisclaimers() {
                        throw new RuntimeException(); // TODO Auto-generated method stub
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
