/* Copyright (c) 2011 The University of Kansas Medical Center
 * http://informatics.kumc.edu/ */

package edu.kumc.informatics.heron.servlet;

import edu.kumc.informatics.heron.capsec.Agent;
import edu.kumc.informatics.heron.capsec.AcademicMedicalCenter;
import edu.kumc.informatics.heron.util.CASCheck;
import edu.kumc.informatics.heron.capsec.Sponsor;
import edu.kumc.informatics.heron.capsec.SystemAccessRecords;
import java.io.IOException;
import java.io.PrintWriter;
import javax.servlet.ServletException;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;


/**
 * TODO: this is really test code
 */
public class DeriveCas extends HttpServlet {

        private AcademicMedicalCenter _idvault;
        private SystemAccessRecords _sar;

        @Override
        /**
         * cribbed from http://andykayley.blogspot.com/2007/11/how-to-inject-spring-beans-into.html
         * not type-safe, but simpler than @Autowired magic.
         */
        public void init() {
                _idvault = (AcademicMedicalCenter) SpringServletHelper.getBean(getServletContext(),
                        AcademicMedicalCenter.beanName);
                _sar = (SystemAccessRecords) SpringServletHelper.getBean(getServletContext(),
                        SystemAccessRecords.beanName);
        }

        /**
         * Derive a CASCap from the HttpServletRequest and display its name.
         * @throws ServletException if the request has no attributes from CAS authentication.
         * @throws IOException
         */
        @Override
        protected void doGet(HttpServletRequest q, HttpServletResponse a)
                throws ServletException, IOException {
                PrintWriter out = a.getWriter();
                try {
                        CASCheck guard = CASCheck.asTicket(q);

                        a.setContentType("text/html; charset=utf-8");

                        out.println("<html>"
                                + "<head><title>capability foo</title></head>"
                                + "<body>");
                        out.println(elt("p", "Try: <a href='?cas=1'>cas</a>"));
                        if (q.getParameter("cas") != null) {
                                out.println(elt("p", guard.getName()));
                        }
                        if (q.getParameter("ldap") != null) {
                                out.println(elt("p", "ldap"));
                                Agent who;
                                try {
                                        who = _idvault.affiliate(guard.getName());
                                } catch (SecurityException ex) {
                                        throw new ServletException(ex);
                                }
                                out.println(elt("p", "employee name: " + who.getFullName()));
                                out.println(elt("p", "employee email: " + who.getMail()));

                        }
                        if (q.getParameter("sponsor") != null) {
                                Sponsor who = _sar.asSponsor(guard);
                                out.println(elt("p", "sponsor"));
                                out.println(elt("p", "sponsorship: " + guard.getName()));
                        }
                        out.println("</body></html>");
                } catch (Exception ex) {
                        sendErrorRedirect(q, a, "/error_page.jsp", ex);
                } finally {
                        out.close();
                }
        }

        private String elt(String name, String content) {
                return "<" + name + ">" + content + // escaping
                        "</" + name + ">";
        }


        /**
         * cribbed from http://www.jguru.com/faq/view.jsp?EID=1347
         */
        protected void sendErrorRedirect(HttpServletRequest request,
                HttpServletResponse response, String errorPageURL,
                Throwable e)
                throws ServletException, IOException {
                request.setAttribute("javax.servlet.jsp.jspException", e);
                getServletConfig().getServletContext().
                        getRequestDispatcher(errorPageURL).forward(request,
                        response);
        }
}
