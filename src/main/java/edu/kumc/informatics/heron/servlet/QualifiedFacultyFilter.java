/* @@copyright */

package edu.kumc.informatics.heron.servlet;

import edu.kumc.informatics.heron.capsec.Enterprise;
import edu.kumc.informatics.heron.util.CASCheck;
import java.io.IOException;
import javax.servlet.Filter;
import javax.servlet.FilterChain;
import javax.servlet.FilterConfig;
import javax.servlet.ServletException;
import javax.servlet.ServletRequest;
import javax.servlet.ServletResponse;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

/**
 * Filter out requests that do not come from qualified faculty.
 * For requests that do come from qualified faculty,
 * set the edu.kumc.informatics.heron.servlet.QualifiedFacultyFilter
 * request attribute to the Agent from Enterprise.qualifiedFaculty().
 *
 * @seeAlso Enterprise.qualifiedFaculty()
 * @author dconnolly
 */
public class QualifiedFacultyFilter implements Filter {
        private Enterprise _idvault;

        @Override
        public void init(FilterConfig fc) throws ServletException {
                _idvault = (Enterprise) SpringServletHelper.getBean(fc.getServletContext(),
                        Enterprise.class);
        }

        @Override
        public void doFilter(ServletRequest q, ServletResponse a, FilterChain fc) throws IOException, ServletException {
                HttpServletRequest hq = (HttpServletRequest) q;
                HttpServletResponse ha = (HttpServletResponse) a;
                try {
                        q.setAttribute(QualifiedFacultyFilter.class.getName(),
                                _idvault.qualifiedFaculty(CASCheck.asTicket(hq)));
                } catch (SecurityException e) {
                        ha.sendError(javax.servlet.http.HttpServletResponse.SC_FORBIDDEN);
                        return;
                }
                fc.doFilter(q, a);
        }

        @Override
        public void destroy() {
                _idvault = null; // Surely this is superfluous, given GC.
        }
}
