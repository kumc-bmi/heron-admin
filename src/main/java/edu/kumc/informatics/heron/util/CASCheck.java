/* Copyright (c) 2011 The University of Kansas Medical Center
 * http://informatics.kumc.edu/ */

package edu.kumc.informatics.heron.util;

import edu.kumc.informatics.heron.capsec.Ticket;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.ServletException;

import org.jasig.cas.client.util.AbstractCasFilter;
import org.jasig.cas.client.validation.Assertion;

/**
 * A CASCheck derives other capabilities from a CAS-authenticated HttpServletRequest.
 * @author dconnolly
 * @deprecated in favor of AcademicMedicalCenter.asTicket()
 */
@Deprecated
public class CASCheck implements Ticket {
        private final String _name;

        @Override
        public String getName() {
                return _name;
        }

        protected CASCheck (String name) {
                _name = name;
        }

        protected static final SecurityException denied =
                new SecurityException("no CAS ticket");

        /**
         * Derive a CASCap from a CAS-filtered HttpServletRequest.
         * @param request
         * @return a CASCap that gives access to the name of the authenticated CAS Principal.
         * @throws ServletException if the request's session has no CAS assertion attribute.
         */
        public static CASCheck asTicket(HttpServletRequest request)  throws SecurityException {
                // Rescue Assertion from un-typesafe attribute mapping.
                Assertion it = (Assertion)request.getSession().getAttribute(
                        AbstractCasFilter.CONST_CAS_ASSERTION);
                if (it == null){
                        throw denied;
                }

                return new CASCheck(it.getPrincipal().getName());
        }
}
