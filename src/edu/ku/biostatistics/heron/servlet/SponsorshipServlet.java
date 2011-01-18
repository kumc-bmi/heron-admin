package edu.ku.biostatistics.heron.servlet;

import static edu.ku.biostatistics.heron.base.StaticValues.*;

import java.io.IOException;
import javax.servlet.RequestDispatcher;
import javax.servlet.ServletException;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

import edu.ku.biostatistics.heron.util.BasicUtil;
import edu.ku.biostatistics.heron.util.DBUtil;

/**
 * Servlet implementation class SponsorshipServlet to handle user sponsorship.
 * 
 * D. zhu
 */
public class SponsorshipServlet extends HttpServlet {
	private static final long serialVersionUID = 1L;
	private DBUtil dbUtil = new DBUtil();   
	private BasicUtil bUtil = new BasicUtil();
	
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
			String message = validateInput(request);
			
			if("".equals(message)){
				String result = "User(s) Sponsored Successfully !";
				try{
					dbUtil.insertSponsorships(request);
				}catch(Exception ex){
					result = "Sorry, unexpected error with database update: " + ex.getMessage();
				}
				request.setAttribute(VAL_MESSAGE, result);
				RequestDispatcher rd = request.getRequestDispatcher(GEN_DISPLAY_URL);
				rd.forward(request, response);
			}
			else{
				request.setAttribute(VAL_MESSAGE, message);
				RequestDispatcher rd = request.getRequestDispatcher(SPONSOR_URL);
				rd.forward(request, response);
			}
		}
		else{
			response.sendRedirect(DENIED_URL);
		}
	}
	
	/**
	 * check input.
	 * @param request
	 * @return a string(message) with error info or empty string if no error.
	 */
	private String validateInput(HttpServletRequest request){
		String msg = "";
		String resTitle = request.getParameter("txtRTitle");
		String resDesc = request.getParameter("resDesc");
		String empls = request.getParameter("empIds");
		String nonEmpls = request.getParameter("nonempIds");
		String expDate = request.getParameter("expDate");
		
		if(resTitle==null || resTitle.trim().equals(""))
			msg += "Title of Research is required. ";
		if(resDesc==null || resDesc.trim().equals(""))
			msg += "Description of the Research is required. ";
		if((empls==null || empls.trim().equals("")) && (nonEmpls==null || nonEmpls.trim().equals("")))
			msg += "Must enter employee Id(s) or non-KUMC employee Id(s). ";
		if((expDate!=null&& !expDate.trim().equals("")) && !bUtil.checkDateFormat(expDate))
			msg += "Date format invalid. ";
		String emplIdLdapMsg =  bUtil.ldapCheck(empls);
		if(!"".equals(emplIdLdapMsg))
			msg += "The following employee id not in LDAP: "+emplIdLdapMsg+". ";
		String nonEmplIdLdapMsg =  bUtil.ldapCheck(nonEmpls);
		if(!"".equals(nonEmplIdLdapMsg))
			msg += "The following non-employee id not in LDAP: "+nonEmplIdLdapMsg;
	    return msg;
	}

}
