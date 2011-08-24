/* Copyright (c) 2011 The University of Kansas Medical Center
 * http://informatics.kumc.edu/ */
package edu.kumc.informatics.heron.servlet;

import java.util.HashMap;
import java.util.Map;

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

// http://www.antlr.org/wiki/display/ST/Five+minute+Introduction
//import org.antlr.stringtemplate.StringTemplate;

/**
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

        private Agent _affiliate;
        private Sponsor _sponsor;
        private RepositoryUser _user;

        /**
         * @param fallback value to return in case affiliate hasn't been set.
         */
        public String getFullName(String fallback) {
                if (_affiliate == null) {
                        return fallback;
                } else {
                        return _affiliate.getFullName();
                }
        }

        /**
         * @param fallback value to return in case affiliate hasn't been set.
         */
        public String getMail(String fallback) {
                if (_affiliate == null) {
                        return fallback;
                } else {
                        return _affiliate.getMail();
                }
        }

        public Boolean canSponsor() {
                return _sponsor != null;
        }

        // This is part of the public interface because it must match config.
        public static final String VIEW_NAME = "myChecklist";
        // Part of public interface because it must match template usage.
        public static final String FULL_NAME = "fullName";
        public static final String REPOSITORY_TOOL = "repositoryTool";
        public static final String SPONSORSHIP_FORM = "sponsorshipForm";
        
        @Override
        public ModelAndView handleRequest(HttpServletRequest q, HttpServletResponse a)
                throws ServletException {


                Ticket ticket = _enterprise.asTicket(q);
                try {
                        _affiliate = _enterprise.affiliate(ticket.getName());

                        try {
                                _user = _sar.asUser(ticket);
                        } catch (NoPermissionException ex) {
                                logger.debug("not a repository user:" + ticket.getName());
                        } catch (NameNotFoundException ex) {
                                logger.debug("not a repository user:" + ticket.getName());
                        }
                        
                        try {
                                _sponsor = _sar.asSponsor(ticket);
                        } catch (NoPermissionException ex) {
                                logger.debug("not allowed to sponsor:" + ticket.getName());
                        }
                } catch (NameNotFoundException ex) {
                        // Nobody in the enterprise by that name/id/
                }
                logger.info("Returning checklist view with " + getFullName("fallback"));

                Map<String, String> model = new HashMap<String, String>();
                model.put(FULL_NAME, getFullName(""));
                model.put(REPOSITORY_TOOL, _user == null ? null : "TODO:i2b2addr@@");
                model.put(SPONSORSHIP_FORM, _sponsor == null ? null : "TODO:sponsorhipForm@@");
                
                return new ModelAndView(VIEW_NAME, model);
        }
}