package edu.ku.biostatistics.heron.servlet;

import static edu.ku.biostatistics.heron.base.StaticValues.*;

import java.io.IOException;
import java.util.Properties;

import javax.servlet.RequestDispatcher;
import javax.servlet.ServletException;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import javax.servlet.http.HttpSession;

import edu.ku.biostatistics.heron.util.BasicUtil;
import edu.ku.biostatistics.heron.util.DBUtil;
import edu.ku.biostatistics.heron.util.LdapUtil;
import edu.ku.biostatistics.heron.util.StaticDataUtil;

/**
 * Servlet implementation class SponsorshipServlet to handle user sponsorship.
 * 
 * D. zhu
 */
public class SponsorshipServlet extends HttpServlet {
	private static final long serialVersionUID = 1L;
	private DBUtil dbUtil = new DBUtil();   
	private BasicUtil bUtil = new BasicUtil();
	private LdapUtil ldapUtil = new LdapUtil();
	private Properties props = StaticDataUtil.getSoleInstance().getProperties();
	
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
		String initType = request.getParameter("init_type");
		
		//initial display
		if(initType!=null){
			String uid = request.getRemoteUser();
			String[] info = ldapUtil.getUserInfo(uid);	
			HttpSession session = request.getSession();
			session.setAttribute(USER_FULL_NAME, info[0]);
			session.setAttribute(USER_TITLE, info[2]);
			boolean isQualified = true;//checkQualification(info[1],info[3],uid);
			
			if(!isQualified){
				String message = "sorry, only qualified falcuties can use this functionality.";
				request.setAttribute(VAL_MESSAGE, message);
				RequestDispatcher rd = request.getRequestDispatcher(GEN_DISPLAY_URL);
				rd.forward(request, response);
			}
			else{
				String url = initType.equals(VIEW_ONLY)?SPONSOR_URL:DATA_USAGE_URL;
				RequestDispatcher rd = request.getRequestDispatcher(url);
				rd.forward(request, response);
			}
		}
		else if("Accept and Submit".equals(type)){//submit sponsorship
			String spnsrType = request.getParameter("spnsr_type");
			String backUrl = spnsrType.equals(VIEW_ONLY)?SPONSOR_URL:DATA_USAGE_URL;
			String message = validateInput(request);
			
			if("".equals(message)){
				String result = spnsrType.equals(VIEW_ONLY)?"User(s) Sponsored Successfully !":"Data Usage Agreement Submitted Successfully!";
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
				RequestDispatcher rd = request.getRequestDispatcher(backUrl);
				rd.forward(request, response);
			}
		}
		else{//deny/cancel sponsorship
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
			msg += "Expiration Date format invalid. ";
		String emplIdLdapMsg =  bUtil.ldapCheck(empls);
		if(!"".equals(emplIdLdapMsg))
			msg += "The following employee id not in LDAP: "+emplIdLdapMsg+". ";
		String nonEmplIdLdapMsg =  bUtil.ldapCheck(nonEmpls);
		if(!"".equals(nonEmplIdLdapMsg))
			msg += "The following non-employee id not in LDAP: "+nonEmplIdLdapMsg;
		String spnsrType = request.getParameter("spnsr_type");
		
		if(spnsrType.equals(DATA_ACCESS)){
			String sigName = request.getParameter("txtName");
			String sigDate = request.getParameter("txtSignDate");
			
			if(sigName==null || sigName.trim().equals(""))
				msg += "Signature is required. ";
			if(sigDate==null || sigDate.trim().equals(""))
				msg += "Signature Date is required. ";
			else if(!bUtil.checkDateFormat(sigDate))
			    	msg += "Signature Date format is wrong.";
		}
	    return msg;
	}

	/**
	 * For now, check if user is a qualified faculty.
	 * aware of the rules will change. Otherwise, build/use a common util method.
	 * @param facFlag
	 * @param jobCode
	 * @param uid
	 * @return true if yes, false otherwise.
	 */
	private boolean checkQualification(String facFlag,String jobCode,String uid){
		if(facFlag!=null && facFlag.equals("Y") && !jobCode.equals(props.getProperty(EXCLUDED_JOBCODE)))
			return true;
		else 
			return false;
		//return dbUtil.isSpecialSponsor(uid); TODO: future logic.
	}
}
