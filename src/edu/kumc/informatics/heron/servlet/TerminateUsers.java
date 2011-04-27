package edu.kumc.informatics.heron.servlet;

import static edu.kumc.informatics.heron.base.StaticValues.GEN_DISPLAY_URL;
import static edu.kumc.informatics.heron.base.StaticValues.HOME_URL;
import static edu.kumc.informatics.heron.base.StaticValues.SAA_URL;
import static edu.kumc.informatics.heron.base.StaticValues.VAL_MESSAGE;

import java.io.IOException;

import javax.servlet.RequestDispatcher;
import javax.servlet.ServletException;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

import static edu.kumc.informatics.heron.base.StaticValues.*;
import edu.kumc.informatics.heron.util.DBUtil;

/**
 * Servlet implementation class TerminateUsers
 */
public class TerminateUsers extends HttpServlet {
	private static final long serialVersionUID = 1L;
	private DBUtil dUtil = new DBUtil();   
    /**
     * @see HttpServlet#HttpServlet()
     */
    public TerminateUsers() {
        super();
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
			String id = request.getParameter("userlist");
			String reason = request.getParameter("resDesc");
			
			if(id==null||id.trim().equals("")){
				request.setAttribute(VAL_MESSAGE,"select an ID from the list please");
				RequestDispatcher rd = request.getRequestDispatcher(TERM_URL);
				rd.forward(request, response);
			}
			else{
				String result = dUtil.termSponsorship(id,TERM_ACTION,reason);
				request.setAttribute(VAL_MESSAGE, result);
				RequestDispatcher rd = request.getRequestDispatcher(GEN_DISPLAY_URL);
				rd.forward(request, response);
			}
		}
		else{
			response.sendRedirect(HOME_URL);
		}
	}

}
