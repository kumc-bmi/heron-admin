/* Copyright (c) 2011 The University of Kansas Medical Center
 * http://informatics.kumc.edu/ */

package edu.kumc.informatics.heron.util;

import javax.servlet.http.HttpServletRequest;
import javax.servlet.ServletException;

import org.jasig.cas.client.util.AbstractCasFilter;
import org.jasig.cas.client.validation.Assertion;

/**
 * A CASCheck derives other capabilities from a CAS-authenticated HttpServletRequest.
 * @author dconnolly
 */
public class CASCheck {
        private final String _name;

        private static final ServletException noCAS = new ServletException(
                                "cannot make CASCap without session attribute: " +
                                AbstractCasFilter.CONST_CAS_ASSERTION);

        public String getName() throws ServletException {
                if (_name == null) {
                        throw noCAS;
                }
                return _name;
        }

        /**
         * Derive a CASCap from a CAS-filtered HttpServletRequest.
         * @param request
         * @return a CASCap that gives access to the name of the authenticated CAS Principal.
         * @throws ServletException if the request's session has no CAS assertion attribute.
         */
        public CASCheck (HttpServletRequest request) {
                // Rescue Assertion from un-typesafe attribute mapping.
                Assertion it = (Assertion)request.getSession().getAttribute(
                        AbstractCasFilter.CONST_CAS_ASSERTION);
                if (it == null){
                        _name = null;
                } else {
                        _name = it.getPrincipal().getName();
                }
        }

}
