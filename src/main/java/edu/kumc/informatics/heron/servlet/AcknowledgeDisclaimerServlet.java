package edu.kumc.informatics.heron.servlet;

import static edu.kumc.informatics.heron.base.StaticValues.DENIED_URL;
import static edu.kumc.informatics.heron.base.StaticValues.I2B2_CLIENT_SERVICE;

import java.io.IOException;
import java.util.Properties;

import javax.inject.Inject;
import javax.naming.NoPermissionException;
import javax.servlet.ServletException;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestMethod;

import edu.kumc.informatics.heron.capsec.AcademicMedicalCenter;
import edu.kumc.informatics.heron.capsec.Agent;
import edu.kumc.informatics.heron.capsec.RepositoryUser;
import edu.kumc.informatics.heron.capsec.SystemAccessRecords;
import edu.kumc.informatics.heron.util.StaticDataUtil;

@Controller
public class AcknowledgeDisclaimerServlet { // TODO: rename
        Properties props = StaticDataUtil.getSoleInstance().getProperties();
        @Inject
        public AcknowledgeDisclaimerServlet(AcademicMedicalCenter org, SystemAccessRecords sar) {
                _org = org;
                _sar = sar;
        }

        private final AcademicMedicalCenter _org;
        private final SystemAccessRecords _sar;

        public static final String ERROR_VIEW_NAME = "errorPage";
        
        /**
         * @throws ServletException in case of missing CAS ticket
         * @throws IOException 
         * @see HttpServlet#doPost(HttpServletRequest request,
         *      HttpServletResponse response)
         */
//TODO        @RequestMapping(value="/AcknowledgeDisclaimerServlet", method = RequestMethod.POST)
        public String acknowledge(HttpServletRequest request,
                        HttpServletResponse response) throws ServletException {
                RepositoryUser u;

                try {
                        try {
                                u = _sar.repositoryUser(_sar.qualifiedUser(request));
                        } catch (NoPermissionException e) {
                                response.sendError(HttpServletResponse.SC_FORBIDDEN);
                                return ERROR_VIEW_NAME;
                        }
                } catch (IOException e) {
                        throw new ServletException(e);
                }

                u.acknowledgedRecentDisclaimers();

                return "redirect:" + props.getProperty(I2B2_CLIENT_SERVICE);
        }

}
