/* Copyright (c) 2011 The University of Kansas Medical Center
 * http://informatics.kumc.edu/ */

package edu.kumc.informatics.heron.servlet;

import javax.servlet.ServletContext;
import org.springframework.web.context.WebApplicationContext;
import org.springframework.web.context.support.WebApplicationContextUtils;

/**
 * cribbed from http://andykayley.blogspot.com/2007/11/how-to-inject-spring-beans-into.html
 * so much for IoC and type-safety, but simpler than @Autowired magic.
 * @author dconnolly
 */
public class SpringServletHelper {
        public static Object getBean(ServletContext ctx, String name) {
                WebApplicationContext springContext =
                        WebApplicationContextUtils.getWebApplicationContext(ctx);
                return springContext.getBean(name);
        }
}
