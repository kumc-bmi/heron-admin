/* Copyright (c) 2011 The University of Kansas Medical Center
 * http://informatics.kumc.edu/ */

package edu.kumc.informatics.heron.capsec;

import java.util.Date;

import javax.naming.NameNotFoundException;
import javax.naming.NoPermissionException;
import javax.servlet.ServletException;
import javax.servlet.http.HttpServletRequest;

import edu.kumc.informatics.heron.util.Functional.Function1;

/**
 *
 * @author dconnolly
 */
public interface AcademicMedicalCenter {
        /**
         * Look up an affiliated agent by name.
         * @param name
         * @return an agent of this enterprise
         * @throws NameNotFoundException if there is no agent by that name
         *         in this enterprise.
         */
        Agent affiliate(String name) throws NameNotFoundException;

        Agent affiliate(HttpServletRequest q) throws ServletException;

        <T> T withFaculty(Agent supposedFaculty, Function1<Agent, T> f)
        		 throws NoPermissionException;
        public final NoPermissionException notFaculty = new NoPermissionException();
        
        Date trainedThru(Agent a) throws NoPermissionException;

        String beanName = "enterprise";
}
