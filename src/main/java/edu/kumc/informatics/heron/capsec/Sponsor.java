/* Copyright (c) 2011 The University of Kansas Medical Center
 * http://informatics.kumc.edu/ */

package edu.kumc.informatics.heron.capsec;

import java.security.acl.NotOwnerException;

/**
 *
 * @author dconnolly
 */
public interface Sponsor {
        /**
         *
         * @param title
         * @param who
         * TODO: more params
         * @throws NotOwnerException if who is not from the same enterprise
         *         as this sponsor.
         */
	public void fileRequest(String title, Agent who)
                throws NotOwnerException;
}
