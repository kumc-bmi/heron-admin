/* Copyright (c) 2011 The University of Kansas Medical Center
 * http://informatics.kumc.edu/ */

package edu.kumc.informatics.heron.capsec;

import java.security.acl.NotOwnerException;

import javax.naming.NoPermissionException;
import javax.servlet.ServletException;
import javax.servlet.http.HttpServletRequest;

/**
 * 
 * @author dconnolly
 */
public interface SystemAccessRecords {
	interface Qualification {
		Agent forWhom();
	}
	
	/**
	 * TODO: carefully document this interface
	 * 
	 * @param who
	 * @return
	 * @throws NoPermissionException
	 * @throws ServletException 
	 * @throws IOException 
	 * @throws NotOwnerException 
	 */
	Qualification facultyUser(HttpServletRequest q) throws NoPermissionException, ServletException;

	Qualification sponsoredUser(HttpServletRequest q) throws NoPermissionException, ServletException;

	Qualification executiveUser(HttpServletRequest q) throws NoPermissionException, ServletException;

	Qualification qualifiedUser(HttpServletRequest q) throws NoPermissionException, ServletException;

        NoPermissionException nosig = new NoPermissionException();
        NoPermissionException notSponsored = new NoPermissionException();
        NoPermissionException notExecutive = new NoPermissionException();
        NoPermissionException trainingOutOfDate = new NoPermissionException();

        RepositoryUser repositoryUser(Qualification q) throws NoPermissionException;
        
	/**
	 * Turn a request into a Sponsor, provided the request is from a qualified
	 * faculty member who signed the system access agreement.
	 * 
	 * @param who
	 * @return
	 * @throws NoPermissionException
	 * @throws ServletException 
	 * @throws IOException 
	 */
	Sponsor asSponsor(HttpServletRequest q) throws NoPermissionException, ServletException;

	public static final String beanName = "sar";
}
