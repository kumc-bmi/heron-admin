/* Copyright (c) 2011 The University of Kansas Medical Center
 * http://informatics.kumc.edu/ */

package edu.kumc.informatics.heron.capsec;

/**
 *
 * @author dconnolly
 */
public interface Agent {
		/**
		 * Get the given and surname of this agent, separated by a space.
		 * See
		 * <a href="http://tools.ietf.org/html/rfc4519#section-2.32">section 2.32 on surname (sn)</a>,
		 * <a href="http://tools.ietf.org/html/rfc4519#section-2.12">section 2.12 on given name (givenName)</a>.
		 */
        public String getFullName();

        /**
         * Get the title of this agent in their organizational context.
         * per <a href="http://tools.ietf.org/html/rfc4519#section-2.38">section 2.38 of the LDAP spec<a>
         */
        public String getTitle();

        public String getMail();
}
