package edu.kumc.informatics.heron.servlet;

import static edu.kumc.informatics.heron.base.StaticValues.*;
import java.io.IOException;
import javax.servlet.RequestDispatcher;
import javax.servlet.ServletException;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

import edu.kumc.informatics.heron.util.DBUtil;

/**
 * Servlet implementation class SponsorshipApprovalServlet
 */
public class SponsorshipApprovalServlet extends HttpServlet {
	private static final long serialVersionUID = 1L;
    private DBUtil dUtil = new DBUtil();
    /**
     * @see HttpServlet#HttpServlet()
     */
    public SponsorshipApprovalServlet() {
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
		String action = request.getParameter("submitbtn");
		
		if("Submit".equals(action)){
			String result = dUtil.approveSponsorship(request);
			request.setAttribute(VAL_MESSAGE, result);
			RequestDispatcher rd = request.getRequestDispatcher(GEN_DISPLAY_URL);
			rd.forward(request, response);
		}
		else{
			response.sendRedirect(HOME_URL);
		}
	}
}
