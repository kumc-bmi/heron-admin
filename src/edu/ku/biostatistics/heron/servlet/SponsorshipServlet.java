package edu.ku.biostatistics.heron.servlet;

import static edu.ku.biostatistics.heron.base.StaticValues.*;
import java.io.IOException;

import javax.servlet.RequestDispatcher;
import javax.servlet.ServletException;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

import edu.ku.biostatistics.heron.util.DBUtil;

/**
 * Servlet implementation class SponsorshipServlet
 */
public class SponsorshipServlet extends HttpServlet {
	private static final long serialVersionUID = 1L;
	private DBUtil dbUtil = new DBUtil();   
    /**
     * @see HttpServlet#HttpServlet()
     */
    public SponsorshipServlet() {
        super();
        // TODO Auto-generated constructor stub
    }

	/**
	 * @see HttpServlet#doGet(HttpServletRequest request, HttpServletResponse response)
	 */
	protected void doGet(HttpServletRequest request, HttpServletResponse response) throws ServletException, IOException {
		doPost(request,response);
	}

	/**
	 * @see HttpServlet#doPost(HttpServletRequest request, HttpServletResponse response)
	 */
	protected void doPost(HttpServletRequest request, HttpServletResponse response) throws ServletException, IOException {
		String type = request.getParameter("agreementbtn");
		
		if("Accept and Submit".equals(type)){
			dbUtil.insertSponsorships(request);
			request.setAttribute(VAL_MESSAGE, "User(s) Sponsored Successfully !");
			RequestDispatcher rd = request.getRequestDispatcher(GEN_DISPLAY_URL);
			rd.forward(request, response);
		}
		else{
			response.sendRedirect(DENIED_URL);
		}
		
	}

}
