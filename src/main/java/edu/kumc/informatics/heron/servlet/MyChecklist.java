/* Copyright (c) 2011 The University of Kansas Medical Center
 * http://informatics.kumc.edu/ */
package edu.kumc.informatics.heron.servlet;

import javax.inject.Inject;
import javax.naming.NameNotFoundException;
import javax.naming.NoPermissionException;
import javax.servlet.ServletException;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;
import org.springframework.web.servlet.ModelAndView;
import org.springframework.web.servlet.mvc.Controller;

import edu.kumc.informatics.heron.capsec.AcademicMedicalCenter;
import edu.kumc.informatics.heron.capsec.Agent;
import edu.kumc.informatics.heron.capsec.RepositoryUser;
import edu.kumc.informatics.heron.capsec.Sponsor;
import edu.kumc.informatics.heron.capsec.SystemAccessRecords;
import edu.kumc.informatics.heron.capsec.Ticket;

/**
 * MyChecklist is a HERON access checklist controller.
 * 
 * See handleRequest() for details.
 * 
 * @author dconnolly
 */
public class MyChecklist implements Controller {

        protected final Log logger = LogFactory.getLog(getClass());

        private AcademicMedicalCenter _enterprise;
        private SystemAccessRecords _sar;

        /**
         * Construct HERON checklist model from organization and system records.
         * @param e organization for directory lookups
         * @param sar access records
         */
        @Inject
        public MyChecklist(final AcademicMedicalCenter e, final SystemAccessRecords sar) {
                _enterprise = e;
                _sar = sar;
        }

        /**
         * Name for this view is "myChecklist".
         * TODO: cite relevant part of Spring MVC docs.
         */
        public static final String VIEW_NAME = "myChecklist";

        public enum ChecklistProperty {
        	AFFILIATE("affiliate"),
        	SPONSOR("sponsor"),
        	REPOSITORY_USER("repositoryUser"),
        	REPOSITORY_TOOL("repositoryTool"),
        	SPONSORSHIP_FORM("sponsorshipForm");
        	final private String label;
        	ChecklistProperty(String l) {
        		label = l;
        	}
        	@Override
        	public String toString() {
        		return label;
        	}
        }

        /**
         * Try to get an affiliate, repository user, and sponsor based on a request.
         * 
         * Given a request filtered through a CAS authentication filter:
         * 
         * 1. Try to get an affiliate from our AcademicMedicalCenter.
         * 3. Try to get a repository user based on system access records.
         * 2. Try to get a sponsor based on system access records and faculty qualifications.
         * 
         * Then construct a model with the results, using property names from ChecklistProperty.
         * 
         * @throws ServletException if the request, q, has no CAS assertion.
         */
        @Override
        public ModelAndView handleRequest(HttpServletRequest q, HttpServletResponse a)
        		throws ServletException {
        	Agent affiliate = null;
            Sponsor sponsor = null;
            RepositoryUser user = null;

                Ticket ticket = _enterprise.requestTicket(q);
                try {
                        affiliate = _enterprise.affiliate(ticket.getName());

                        try {
                                user = _sar.asUser(ticket);
                        } catch (NoPermissionException ex) {
                                logger.debug("no system access agreement on record:" + ticket.getName());
                        } catch (NameNotFoundException ex) {
                        	// this can't happen if we already got an affiliate
                        	throw new AssertionError(ex);
                        }
                        
                        try {
                                sponsor = _sar.asSponsor(ticket);
                        } catch (NoPermissionException ex) {
                                logger.debug("not allowed to sponsor:" + ticket.getName());
                        }
                } catch (NameNotFoundException ex) {
                        // Nobody in the enterprise by that name/id/
                }

                ModelAndView mv = new ModelAndView(VIEW_NAME);
                mv.addObject(ChecklistProperty.AFFILIATE.toString(), affiliate);

                mv.addObject(ChecklistProperty.SPONSOR.toString(), sponsor);
        		mv.addObject(ChecklistProperty.SPONSORSHIP_FORM.toString(),
        				sponsor != null ? "TODO:sponsorhipForm@@" : null); // TODO

        		mv.addObject(ChecklistProperty.REPOSITORY_USER.toString(), user);
        		mv.addObject(ChecklistProperty.REPOSITORY_TOOL.toString(),
        				user != null ? "TODO:i2b2addr@@" : null); // TODO

        		return mv;
        }
}