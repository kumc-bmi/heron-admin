package edu.kumc.informatics.heron.servlet;

import static edu.kumc.informatics.heron.base.StaticValues.DENIED_URL;
import static edu.kumc.informatics.heron.base.StaticValues.I2B2_CLIENT_SERVICE;

import java.io.IOException;
import java.util.Properties;

import javax.servlet.ServletException;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

import edu.kumc.informatics.heron.util.DBUtil;
import edu.kumc.informatics.heron.util.StaticDataUtil;

/**
 * Servlet implementation class AcknowledgeDisclaimerServlet
 */
public class AcknowledgeDisclaimerServlet extends HttpServlet {
	private static final long serialVersionUID = 1L;
	private DBUtil dbUtil = new DBUtil();     
	private Properties props = StaticDataUtil.getSoleInstance().getProperties();
    /**
     * @see HttpServlet#HttpServlet()
     */
    public AcknowledgeDisclaimerServlet() {
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
		String type = request.getParameter("submitbtn");
		String uid = request.getRemoteUser();
		
		if("Acknowledge".equals(type)){
			dbUtil.updateDisclaimerAckowledgement(uid);
			response.sendRedirect(props.getProperty(I2B2_CLIENT_SERVICE));
		}
		else{
			response.sendRedirect(DENIED_URL);
		}
	}

}
