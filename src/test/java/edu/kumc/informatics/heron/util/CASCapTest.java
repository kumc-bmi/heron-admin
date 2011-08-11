/* Copyright (c) 2011 The University of Kansas Medical Center
 * http://informatics.kumc.edu/ */

package edu.kumc.informatics.heron.util;

import java.io.IOException;
import javax.servlet.ServletException;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import javax.servlet.http.HttpSession;
import org.junit.Test;

import org.junit.runner.RunWith;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.SpringJUnit4ClassRunner;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;
import org.springframework.mock.web.MockServletContext;
import org.springframework.test.annotation.ExpectedException;

/**
 * @@TODO: move these tests
 * @author dconnolly
 */
@RunWith(SpringJUnit4ClassRunner.class)
@ContextConfiguration(locations={"classpath:cas-context.xml"})
public class CASCapTest {
        MockHttpServletRequest _q;

        MockHttpServletResponse _a;

        public CASCapTest() {
                _q = new MockHttpServletRequest(new MockServletContext(), "GET", "/");
                HttpSession ensure_session = _q.getSession(true);
                _a = new MockHttpServletResponse();
        }

        @Test
        @ExpectedException(SecurityException.class)
        public void preventUnauthenticatedRequests() throws ServletException, IOException {
                HttpServlet s0 = new CASCapTestServlet();
                s0.service(_q, _a);
        }

        @Test
        /**
         * TODO
         */
        public void supportAuthenticatedRequests() throws ServletException, IOException {
        }

        static class CASCapTestServlet extends HttpServlet {
                @Override
                public void doGet(HttpServletRequest q, HttpServletResponse a) throws ServletException, IOException {
                        a.setContentType("text/plain");
                        CASCheck cap0 = CASCheck.asTicket(q);
                        a.getWriter().print(cap0.getName());
                }
        }
}

