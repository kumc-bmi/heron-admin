/* @@copyright */

package edu.kumc.informatics.heron.servlet;

import java.io.IOException;
import javax.naming.NoPermissionException;
import javax.servlet.Filter;
import javax.servlet.FilterChain;
import javax.servlet.FilterConfig;
import javax.servlet.ServletException;
import javax.servlet.ServletRequest;
import javax.servlet.ServletResponse;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import edu.kumc.informatics.heron.capsec.AcademicMedicalCenter;
import edu.kumc.informatics.heron.capsec.Agent;
import edu.kumc.informatics.heron.util.Functional.Function1;

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
        private AcademicMedicalCenter _idvault;

        @Override
        public void init(FilterConfig fc) throws ServletException {
                _idvault = (AcademicMedicalCenter) SpringServletHelper.getBean(fc.getServletContext(),
                        AcademicMedicalCenter.beanName);
        }

        // TODO: move to Functional
        Function1<Agent, Agent> identity = new Function1<Agent, Agent>() {
		@Override
		public Agent apply(Agent x) {
			return x;
		}};
		
        @Override
        public void doFilter(ServletRequest q, ServletResponse a, FilterChain fc) throws IOException, ServletException {
                HttpServletRequest hq = (HttpServletRequest) q;
                HttpServletResponse ha = (HttpServletResponse) a;
                try {
                	Agent who = _idvault.affiliate(hq);
                	
                	_idvault.withFaculty(who, identity);
                	// todo: "bigger" type that avoids doing withFaculty again?
                	q.setAttribute(QualifiedFacultyFilter.class.getName(), who);
                } catch (NoPermissionException ex) {                        
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
