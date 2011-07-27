/* Copyright (c) 2011 The University of Kansas Medical Center
 * http://informatics.kumc.edu/ */

package edu.kumc.informatics.heron.servlet;

import edu.kumc.informatics.heron.util.CASCheck;
import edu.kumc.informatics.heron.util.EnterpriseAuthority;
import java.io.IOException;
import java.io.PrintWriter;
import javax.naming.NamingException;
import javax.servlet.ServletException;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import org.springframework.web.context.WebApplicationContext;
import org.springframework.web.context.support.WebApplicationContextUtils;


/**
 * TODO: this is really test code
 */
public class DeriveCas extends HttpServlet {

        private EnterpriseAuthority _idvault;

        @Override
        /**
         * cribbed from http://andykayley.blogspot.com/2007/11/how-to-inject-spring-beans-into.html
         * not type-safe, but simpler than @Autowired magic.
         */
        public void init() {
                WebApplicationContext springContext =
                        WebApplicationContextUtils.getWebApplicationContext(getServletContext());
                _idvault = (EnterpriseAuthority) springContext.getBean("enterpriseAuthority");
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
                        CASCheck guard = new CASCheck(q);

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
                                try {
                                        out.println(elt("p", "employee name: " + _idvault.getFullName(guard)));
                                        out.println(elt("p", "employee email: " + _idvault.getMail(guard)));
                                } catch (NamingException ex) {
                                        throw new ServletException(ex);
                                }
                        }
                        if (q.getParameter("sponsor") != null) {
                                out.println(elt("p", "sponsor"));
                                out.println(elt("p", "sponsorship: " + _idvault.sponsorship(guard)));
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
