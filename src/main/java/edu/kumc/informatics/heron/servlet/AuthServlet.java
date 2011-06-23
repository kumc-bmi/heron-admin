/**
 * authentication. flow controller
 * dongsheng zhu
 */
package edu.kumc.informatics.heron.servlet;

import java.io.IOException;
import java.util.Date;
import java.util.GregorianCalendar;
import java.util.Properties;

import javax.servlet.RequestDispatcher;
import javax.servlet.ServletException;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import javax.servlet.http.HttpSession;

import static edu.kumc.informatics.heron.base.StaticValues.*;
import edu.kumc.informatics.heron.util.DBUtil;
import edu.kumc.informatics.heron.util.LdapUtil;
import edu.kumc.informatics.heron.util.StaticDataUtil;

public class AuthServlet extends HttpServlet {
	private static final long serialVersionUID = 1L;
    private Properties props = StaticDataUtil.getSoleInstance().getProperties();
    private DBUtil dbUtil = new DBUtil();
    private LdapUtil ldapUtil = new LdapUtil();
    
    /**
     * @see HttpServlet#HttpServlet()
     */
    public AuthServlet() {
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
		String uid = request.getRemoteUser();
		String[] info = ldapUtil.getUserInfo(uid);	
		HttpSession session = request.getSession();
		session.setAttribute(USER_FULL_NAME, info[0]);
		session.setAttribute(USER_TITLE, info[2]);
		boolean isQualified = checkQualification(info[1],info[3],uid,request.getParameter("init_type"));
		
		if(!isQualified){
			String msg = "Sorry, It seems you are not a qualified faculty. If you are a sponsored user, please make sure it is approved by DROC and not expired.<p></p>"+
				"Please contact heron support team (heron-admin@kumc.edu)or HR/identity management team if you believe you are qualified. <p>"+
				"Thanks.";
			request.setAttribute(VAL_MESSAGE, msg);
			RequestDispatcher rd = request.getRequestDispatcher(GEN_DISPLAY_URL);
			rd.forward(request, response);
		}
		else{
			Date chalkExpDate = dbUtil.checkChalkTraining(request);
			boolean trained = (chalkExpDate == null || new GregorianCalendar().after(chalkExpDate))?false:true;
				
			if(!trained){
				String trainingDetailMsg = chalkExpDate==null?"you are not HSC/HIPPA trained. ":"your training has expired at "+chalkExpDate.toString();
				String msg = "Sorry, It seems "+trainingDetailMsg+" <p></p>"+
					"Please contact heron support team (heron-admin@kumc.edu) if you believe this info is not correct. <p>"+
					"For HSC/HIPPA training, please go to <a href=\"http://www2.kumc.edu/chalk3/default.aspx\">CHALK</a><p></p>"+
					"Thanks.";
				request.setAttribute(VAL_MESSAGE, msg);
				RequestDispatcher rd = request.getRequestDispatcher(GEN_DISPLAY_URL);
				rd.forward(request, response);
			}
			else{
				boolean saSigned = dbUtil.isUserAgreementSigned(uid);
				if(!saSigned){
					RequestDispatcher rd = request.getRequestDispatcher(SAA_URL);
					rd.forward(request, response);
				}
				else{
					boolean isDisclaimerRead = dbUtil.isDisclaimerRead(uid);
					if(!isDisclaimerRead){
						RequestDispatcher rd = request.getRequestDispatcher(DISCLAIMER_URL);
						rd.forward(request, response);
					}
					else
						response.sendRedirect(props.getProperty(I2B2_CLIENT_SERVICE));
				}
			}
		}
	}
	
	/**
	 * check if user is a qualified faculty or approved view_only user to use i2b2 web app.
	 * if coming from sponsoring, only check if the user is a qualified faculty.
	 * @param facFlag
	 * @param jobCode
	 * @param uid
	 * @return true if yes, false otherwise.
	 */
	private boolean checkQualification(String facFlag,String jobCode,String uid,String initType){
		if(facFlag!=null && facFlag.equals("Y") && !jobCode.equals(props.getProperty(EXCLUDED_JOBCODE)))
			return true;
		if(dbUtil.isUserExecutive(uid))
			return true;
		if(initType==null||initType.equals("null"))
			return dbUtil.isViewOnlyUserApproved(uid);
		else
			return false;
	}
}