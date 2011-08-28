/* Copyright (c) 2011 The University of Kansas Medical Center
 * http://informatics.kumc.edu/ */
package edu.kumc.informatics.heron.servlet;

import java.util.Date;

import javax.inject.Inject;
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
        	TRAINING_EXPIRED("trainingExpired"),
        	TRAINING_EXPIRATION("trainingExpiration"),
        	EXECUTIVE("executive"),
        	FACULTY("faculty"),
        	SPONSORED("sponsored"), // TODO: think of a better name
        	SPONSOR("sponsor"),
        	SIGNATURE_ON_FILE("signatureOnFile"),
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
        public ModelAndView handleRequest(HttpServletRequest q,
                        HttpServletResponse a) throws ServletException {
                ModelAndView mv = new ModelAndView(VIEW_NAME);
                final Agent affiliate = _enterprise.affiliate(q);
                mv.addObject(ChecklistProperty.AFFILIATE.toString(), affiliate);
                SystemAccessRecords.Qualification execqual = null;
                SystemAccessRecords.Qualification facqual = null;
                SystemAccessRecords.Qualification suqual = null;
                SystemAccessRecords.Qualification qual = null;

                try {
                	Date exp = _enterprise.trainedThru(affiliate);
                	mv.addObject(ChecklistProperty.TRAINING_EXPIRATION.toString(), exp);
                	mv.addObject(ChecklistProperty.TRAINING_EXPIRED.toString(), new Date().after(exp));
                } catch (NoPermissionException np) {
                	// I think the StringTemplate convention is null rather than absent.
                	mv.addObject(ChecklistProperty.TRAINING_EXPIRATION.toString(), null);
                	mv.addObject(ChecklistProperty.TRAINING_EXPIRED.toString(), true);
                }

                try {
                	execqual = _sar.executiveUser(q);
                } catch (NoPermissionException notexec) {
                }
                mv.addObject(ChecklistProperty.EXECUTIVE.toString(), execqual);
                try {
                	facqual = _sar.facultyUser(q);
                	qual = facqual;
                } catch (NoPermissionException notfac) {
                }
                mv.addObject(ChecklistProperty.FACULTY.toString(), facqual);
                try {
                	suqual = _sar.sponsoredUser(q);
                	qual = suqual;
                } catch (NoPermissionException notsponsored) {
                }
                mv.addObject(ChecklistProperty.SPONSORED.toString(), suqual);


                RepositoryUser user = null;
                if (qual != null) {
                	try {
                		user = _sar.repositoryUser(qual);
                	} catch (NoPermissionException np) {
                	}
                }
                mv.addObject(ChecklistProperty.REPOSITORY_USER.toString(), user);
                mv.addObject(ChecklistProperty.SIGNATURE_ON_FILE.toString(), user != null);
                mv.addObject(ChecklistProperty.REPOSITORY_TOOL.toString(),
                                user != null ? "TODO:i2b2addr@@" : null); // TODO

                Sponsor sponsor = null;
                try {
                        sponsor = _sar.asSponsor(q);
                } catch (NoPermissionException ex) {
                }
                mv.addObject(ChecklistProperty.SPONSOR.toString(), sponsor);


                mv.addObject(ChecklistProperty.SPONSORSHIP_FORM.toString(),
                                sponsor != null ? "TODO:sponsorhipForm@@"
                                                : null); // TODO

                return mv;
        }
}