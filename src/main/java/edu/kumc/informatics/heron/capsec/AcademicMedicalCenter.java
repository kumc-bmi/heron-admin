/* Copyright (c) 2011 The University of Kansas Medical Center
 * http://informatics.kumc.edu/ */

package edu.kumc.informatics.heron.capsec;

import java.security.acl.NotOwnerException;
import javax.naming.NameNotFoundException;
import javax.naming.NoPermissionException;
import javax.servlet.http.HttpServletRequest;

/**
 *
 * @author dconnolly
 */
public interface AcademicMedicalCenter {
        
        /**
         * Derive a CASCap from a CAS-filtered HttpServletRequest.
         * @param request
         * @return a CASCap that gives access to the name of the authenticated CAS Principal.
         * @throws ServletException if the request's session has no CAS assertion attribute.
         */
        public Ticket asTicket(HttpServletRequest request)  throws SecurityException;

        /**
         * Look up an affiliated agent by name.
         * @param name
         * @return an agent of this enterprise
         * @throws NameNotFoundException if there is no agent by that name
         *         in this enterprise.
         */
        Agent affiliate(String name) throws NameNotFoundException;

        /**
         * Look up a qualified faculty given login credentials.
         * @param who
         * @return
         * @throws NoPermissionException when the ticket provides insufficient
         *         credentials to look up a qualified faculty member.
         */
        Agent qualifiedFaculty(Ticket who) throws NoPermissionException;

        /**
         * Verify that an agent is from this enterprise.
         * @param who
         * @return
         * @throws NotOwnerException
         */
        Agent recognize(Agent who) throws NotOwnerException;

        public static final String beanName = "enterprise";
}
