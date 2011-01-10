/**
 *  servlet to handle system access page request
 * 
 * Dongsheng Zhu
 */
package edu.ku.biostatistics.heron.servlet;

import static edu.ku.biostatistics.heron.base.StaticValues.DENIED_URL;
import static edu.ku.biostatistics.heron.base.StaticValues.I2B2_CLIENT_SERVICE;
import java.io.IOException;
import java.util.Properties;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import javax.servlet.RequestDispatcher;
import javax.servlet.ServletException;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import edu.ku.biostatistics.heron.util.DBUtil;
import edu.ku.biostatistics.heron.util.StaticDataUtil;
import static edu.ku.biostatistics.heron.base.StaticValues.*;

/**
 * Servlet implementation class SystemAccessNoJsServlet
 */
public class SysAccessServlet extends HttpServlet {
	private static final long serialVersionUID = 1L;
	private Properties props = StaticDataUtil.getSoleInstance().getProperties();    
	private DBUtil dbUtil = new DBUtil();
       
    /**
     * @see HttpServlet#HttpServlet()
     */
    public SysAccessServlet() {
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
		String type = request.getParameter("agreementbtn");
		
		if("Accept".equals(type)){
			String message = validateInput(request);
		
			if("".equals(message)){
				dbUtil.insertSystemAccessUser(request);
				if(!dbUtil.isUserInI2b2Database(request.getRemoteUser())){
					dbUtil.insertPMUser(request);
				}
				response.sendRedirect(props.getProperty(I2B2_CLIENT_SERVICE));
			}
			else{
				request.setAttribute(VAL_MESSAGE, message);
				RequestDispatcher rd = request.getRequestDispatcher(SAA_URL);
				rd.forward(request, response);
			}
		}
		else{
			response.sendRedirect(DENIED_URL);
		}
	}
	
	/**
	 * client data validation
	 * @param request
	 * @return error message in a String.
	 */
	private String validateInput(HttpServletRequest request){
		String msg = "";
		String sigName = request.getParameter("txtName");
		String sigDate = request.getParameter("txtSignDate");
		
		if(sigName==null || sigName.trim().equals(""))
			msg += "Signature is required. ";
		if(sigDate==null || sigDate.trim().equals(""))
			msg += "Date is required. ";
		else{
			String expression = "[01][0-2][/](0[1-9]|[12][0-9]|3[01])[/]\\d{4}"; 
			Pattern p = Pattern.compile(expression);
		    Matcher m = p.matcher(sigDate);
		  
		    if(!m.matches())
		    	msg += "Date format is wrong.";
		}
	    return msg;
	}
}
