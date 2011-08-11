/* Copyright (c) 2011 The University of Kansas Medical Center
 * http://informatics.kumc.edu/ */
package edu.kumc.informatics.heron.servlet;

import org.springframework.web.servlet.ModelAndView;

import junit.framework.TestCase;

/**
 *
 * @author dconnolly
 */
public class MyChecklistTest extends TestCase {

    public void testHandleRequestView() throws Exception{
            if (false){ // TODO
        MyChecklist controller = new MyChecklist(null, null);
        ModelAndView modelAndView = controller.handleRequest(null, null);
        assertEquals(MyChecklist.VIEW_NAME, modelAndView.getViewName());
        assertNotNull(modelAndView.getModel());
        String fn = (String) modelAndView.getModel().get("fullName");
        assertNotNull(fn);
            }
    }
}
