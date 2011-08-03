/* Copyright (c) 2011 The University of Kansas Medical Center
 * http://informatics.kumc.edu/ */

package edu.kumc.informatics.heron.capsec;

import javax.naming.NoPermissionException;

/**
 *
 * @author dconnolly
 */
public interface SystemAccessRecords {

        /**
         * Turn a Ticket into a Sponsor, provided the ticket is from
         * a qualified faculty member who signed the system access agreement.
         * @param who
         * @return
         * @throws NoPermissionException
         */
        Sponsor asSponsor(Ticket who) throws NoPermissionException;

        public static final String beanName = "sar";
}
