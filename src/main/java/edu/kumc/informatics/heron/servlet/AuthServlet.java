/**
 * authentication. flow controller
 * dongsheng zhu
 * 
 * TODO: redo this with filters?
 */
package edu.kumc.informatics.heron.servlet;

import java.util.Properties;

import javax.naming.NoPermissionException;
import javax.servlet.ServletException;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestMethod;


import static edu.kumc.informatics.heron.base.StaticValues.*;
import edu.kumc.informatics.heron.capsec.AcademicMedicalCenter;
import edu.kumc.informatics.heron.capsec.Agent;
import edu.kumc.informatics.heron.capsec.SystemAccessRecords;
import edu.kumc.informatics.heron.util.StaticDataUtil;

@Controller
public class AuthServlet {
        private Properties props = StaticDataUtil.getSoleInstance().getProperties();
    
        /**
         * @see HttpServlet#HttpServlet()
         */
        public AuthServlet(AcademicMedicalCenter org, SystemAccessRecords sar) {
                _org = org;
                _sar = sar;
        }
        private final AcademicMedicalCenter _org;
        private final SystemAccessRecords _sar;
    
        @RequestMapping(value="/AuthServlet", method = RequestMethod.POST)
	protected String visitQueryTool(HttpServletRequest request, HttpServletResponse response)
	                throws ServletException {
        	try {
        		_sar.qualifiedUser(request);
        	} catch (NoPermissionException notSponsored) {
        		throw new ServletException(notSponsored);
        	}
                
                // TODO: make this depend on the RepositoryUser?
		return "redirect:" + props.getProperty(I2B2_CLIENT_SERVICE);
	}
}
