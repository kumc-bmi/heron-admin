/**
 *  servlet to handle system access page request
 * 
 * Dongsheng Zhu
 */
package edu.kumc.informatics.heron.servlet;

import static edu.kumc.informatics.heron.base.StaticValues.DATA_USAGE_URL;
import static edu.kumc.informatics.heron.base.StaticValues.DENIED_URL;
import static edu.kumc.informatics.heron.base.StaticValues.DISCLAIMER_URL;
import static edu.kumc.informatics.heron.base.StaticValues.I2B2_CLIENT_SERVICE;
import static edu.kumc.informatics.heron.base.StaticValues.SPONSOR_URL;
import static edu.kumc.informatics.heron.base.StaticValues.USER_FULL_NAME;
import static edu.kumc.informatics.heron.base.StaticValues.USER_PROJ;

import java.io.IOException;
import java.sql.Timestamp;
import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.Properties;
import javax.servlet.RequestDispatcher;
import javax.servlet.ServletException;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import javax.servlet.http.HttpSession;

import edu.kumc.informatics.heron.capsec.AcademicMedicalCenter;
import edu.kumc.informatics.heron.capsec.Agent;
import edu.kumc.informatics.heron.dao.HeronDBDao;
import edu.kumc.informatics.heron.dao.HeronDao;
import edu.kumc.informatics.heron.util.BasicUtil;
import edu.kumc.informatics.heron.util.DBUtil;
import edu.kumc.informatics.heron.util.StaticDataUtil;
import static edu.kumc.informatics.heron.base.StaticValues.*;

/**
 * Servlet implementation class SystemAccessNoJsServlet
 */
public class SysAccessServlet extends HttpServlet {
	private static final long serialVersionUID = 1L;
	private Properties props = StaticDataUtil.getSoleInstance().getProperties();    
	private HeronDBDao _heronData = new HeronDBDao(); // TODO: use interface
	private AcademicMedicalCenter _org; // TODO: inject.
	
        @Override
        public void init() {
                _heronData = (HeronDBDao) SpringServletHelper.getBean(getServletContext(),
                                HeronDBDao.beanName);
                assert _heronData != null;
                assert _org != null; // TODO: this will fail.
        }

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
			Agent who = _org.affiliate(request);
			String uid = who.getUserId();
			
			if("".equals(message)){
				try {
	                                insertSystemAccessUser(request);
                                } catch (ParseException e) {
                                	throw new ServletException(e); //TODO: test hanlding of these problems.
                                }
				if (!_heronData.isUserInI2b2Database(uid)) {
					String projId = StaticDataUtil.getSoleInstance().getProperties()
					                .getProperty(USER_PROJ);
					_heronData.insertPMUser(projId, uid, who.getFullName());
				}
				String sponsorIndctr = request.getParameter("SPNSR");
				String initType = request.getParameter("init_type");

				if (sponsorIndctr != null && !sponsorIndctr.equals("null")) {// coming
					                                                     // from
					                                                     // sponsorship
					String url = initType.equals(HeronDao.AccessType.VIEW_ONLY.toString()) ? SPONSOR_URL : DATA_USAGE_URL;
					RequestDispatcher rd = request.getRequestDispatcher(url);
					rd.forward(request, response);
				}				else{//normal pass of using i2b2
					boolean isDisclaimerRead = _heronData.disclaimer(who).wasRead();
					if(!isDisclaimerRead){
						RequestDispatcher rd = request.getRequestDispatcher(DISCLAIMER_URL);
						rd.forward(request, response);
					}
					else
						response.sendRedirect(props.getProperty(I2B2_CLIENT_SERVICE));
				}
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
		// TODO: else if(!bUtil.checkDateFormat(sigDate))
		//    	msg += "Date format is wrong.";
	    return msg;
	}

        /**
         * add one entry to system_access_users table.
         * @throws ParseException 
         * @throws ServletException 
         */
        public void insertSystemAccessUser(HttpServletRequest request) throws ParseException, ServletException
        {               
        	// TODO: hidden param for XSRF protection, etc.
        	Agent who = _org.affiliate(request);
                String signature = request.getParameter("txtName");
                String signDate = request.getParameter("txtSignDate");
                Long ms = new SimpleDateFormat("MM/dd/yyyy").parse(signDate).getTime();
                _heronData.insertSystemAccessUser(who.getUserId(), who.getFullName(), signature, new Timestamp(ms));
        }        

}
