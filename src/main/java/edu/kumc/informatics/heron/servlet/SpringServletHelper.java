/*
 * To change this template, choose Tools | Templates
 * and open the template in the editor.
 */

package edu.kumc.informatics.heron.servlet;

import java.util.Map;
import javax.servlet.ServletContext;
import org.springframework.web.context.WebApplicationContext;
import org.springframework.web.context.support.WebApplicationContextUtils;

/**
 * TODO: get bean by name rather than by type; the indirection
 *       is a little awkward, but otherwise we lose the whole point
 *       of injection, which is the ability to substitute mock
 *       objects for testing.
 * @author dconnolly
 */
public class SpringServletHelper {
        public static Object getBean(ServletContext ctx, Class c) {
                WebApplicationContext springContext =
                        WebApplicationContextUtils.getWebApplicationContext(ctx);
                Map beans = springContext.getBeansOfType(c);
                return beans.get(beans.keySet().iterator().next());
        }
}
