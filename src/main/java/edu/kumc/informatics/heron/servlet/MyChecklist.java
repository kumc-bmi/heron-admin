/* Copyright (c) 2011 The University of Kansas Medical Center
 * http://informatics.kumc.edu/ */
package edu.kumc.informatics.heron.servlet;

import java.io.IOException;
import javax.inject.Inject;
import javax.servlet.ServletException;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import javax.naming.NameNotFoundException;
import javax.naming.NoPermissionException;

import org.springframework.web.servlet.mvc.Controller;
import org.springframework.web.servlet.ModelAndView;
import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;

import edu.kumc.informatics.heron.capsec.Agent;
import edu.kumc.informatics.heron.capsec.Enterprise;
import edu.kumc.informatics.heron.capsec.Sponsor;
import edu.kumc.informatics.heron.capsec.SystemAccessRecords;
import edu.kumc.informatics.heron.util.CASCheck;

// http://www.antlr.org/wiki/display/ST/Five+minute+Introduction
//import org.antlr.stringtemplate.StringTemplate;

/**
 * @author dconnolly
 */
public class MyChecklist implements Controller {

        protected final Log logger = LogFactory.getLog(getClass());
        
        private Enterprise _enterprise;
        private SystemAccessRecords _sar;

        @Inject
        public void MyChecklist(Enterprise e, SystemAccessRecords sar) {
                _enterprise = e;
                _sar = sar;
        }

        private Agent _affiliate;
        private Sponsor _sponsor;

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

        public static final String VIEW_NAME = "myChecklist";
        
        @Override
        public ModelAndView handleRequest(HttpServletRequest q, HttpServletResponse a)
                throws ServletException, IOException {
                
                if(false){ //@@
                CASCheck ticket = CASCheck.asTicket(q);
                try {
                        _affiliate = _enterprise.affiliate(ticket.getName());
                        
                        try {
                                _sponsor = _sar.asSponsor(ticket);
                        } catch (NoPermissionException ex) {
                                // 
                        }
                } catch (NameNotFoundException ex) {
                        // Nobody in the enterprise by that name/id/
                }
                }
                logger.info("Returning checklist view with " + getFullName("fallback"));
                
                return new ModelAndView(VIEW_NAME, "fullName", getFullName("fallback"));
        }
}