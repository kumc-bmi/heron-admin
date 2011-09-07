package edu.kumc.informatics.heron.servlet;

import static edu.kumc.informatics.heron.base.StaticValues.GEN_DISPLAY_URL;
import static edu.kumc.informatics.heron.base.StaticValues.HOME_URL;
import static edu.kumc.informatics.heron.base.StaticValues.VAL_MESSAGE;

import java.io.IOException;

import javax.inject.Inject;
import javax.servlet.RequestDispatcher;
import javax.servlet.ServletException;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

import static edu.kumc.informatics.heron.base.StaticValues.*;
import edu.kumc.informatics.heron.dao.HeronDBDao;

/**
 * Servlet implementation class TerminateUsers
 */
public class TerminateUsers extends HttpServlet {
	private static final long serialVersionUID = 1L;
	@Inject
	private HeronDBDao _heronData;   
    /**
     * @see HttpServlet#HttpServlet()
     */
    public TerminateUsers() {
        super();
    }

	/**
	 * @see HttpServlet#doPost(HttpServletRequest request, HttpServletResponse response)
	 */
	protected void doPost(HttpServletRequest request, HttpServletResponse response) throws ServletException, IOException {
	        if (_heronData == null) {
	                throw new AssertionError("HeronDBDao injection failed for TerminateUsers");
	        }
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
				String result = _heronData.termSponsorship(id,TERM_ACTION,reason);
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
