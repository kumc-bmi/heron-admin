/**
 * authentication. flow controller
 * dongsheng zhu
 */
package edu.ku.biostatistics.heron.servlet;

import java.io.IOException;
import java.util.Properties;

import javax.servlet.RequestDispatcher;
import javax.servlet.ServletException;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

import static edu.ku.biostatistics.heron.base.StaticValues.*;
import edu.ku.biostatistics.heron.util.DBUtil;
import edu.ku.biostatistics.heron.util.StaticDataUtil;

public class AuthServlet extends HttpServlet {
	private static final long serialVersionUID = 1L;
    private Properties props = StaticDataUtil.getSoleInstance().getProperties();
    private DBUtil dbUtil = new DBUtil();
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
		boolean isQualifiedFaculty = true;//TODO check ldap?

		if(!isQualifiedFaculty){
			RequestDispatcher rd = request.getRequestDispatcher(NOT_QUALIFIED_URL);
			rd.forward(request, response);
		}
		else{
			boolean trained = true;
			if(!trained){
				RequestDispatcher rd = request.getRequestDispatcher(NOT_TRAINED_URL);
				rd.forward(request, response);
			}
			else{
				boolean saSigned = dbUtil.isUserAgreementSigned(request.getRemoteUser());
				if(!saSigned){
					RequestDispatcher rd = request.getRequestDispatcher(SAA_URL);
					rd.forward(request, response);
				}
				else{
					response.sendRedirect(props.getProperty(I2B2_CLIENT_SERVICE));
				}
			}
		}
	}
}
