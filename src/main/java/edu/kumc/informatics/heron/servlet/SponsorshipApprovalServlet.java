package edu.kumc.informatics.heron.servlet;

import static edu.kumc.informatics.heron.base.StaticValues.*;
import java.io.IOException;
import javax.servlet.RequestDispatcher;
import javax.servlet.ServletException;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestMethod;

import edu.kumc.informatics.heron.capsec.DROCSponsoring;
import edu.kumc.informatics.heron.util.DBUtil;

@Controller
public class SponsorshipApprovalServlet {


//TODO	@RequestMapping(value="/SponsorshipApprovalServlet", method = RequestMethod.POST)
        protected String approve(HttpServletRequest request, HttpServletResponse response) throws ServletException, IOException {
/*************
        	DROCSponsoring ds = _sar.drocSponsoring(request);
                String result = dUtil.approveSponsorship(request);
                request.setAttribute(VAL_MESSAGE, result);
                RequestDispatcher rd = request.getRequestDispatcher(GEN_DISPLAY_URL);
                rd.forward(request, response);
**************/
        	return null;
	}
}
