/**
 * auth. flow controller
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
import edu.ku.biostatistics.heron.dao.HeronDBDao;
import edu.ku.biostatistics.heron.util.StaticDataUtil;

public class AuthServlet extends HttpServlet {
	private static final long serialVersionUID = 1L;
    private Properties props = StaticDataUtil.getSoleInstance().getProperties();
    /**
     * @see HttpServlet#HttpServlet()
     */
    public AuthServlet() {
        super();
        // TODO Auto-generated constructor stub
    }

	/**
	 * @see HttpServlet#doGet(HttpServletRequest request, HttpServletResponse response)
	 */
	protected void doGet(HttpServletRequest request, HttpServletResponse response) throws ServletException, IOException {
		// TODO Auto-generated method stub
		doPost(request,response);
	}

	/**
	 * @see HttpServlet#doPost(HttpServletRequest request, HttpServletResponse response)
	 */
	protected void doPost(HttpServletRequest request, HttpServletResponse response) throws ServletException, IOException {
		// TODO Auto-generated method stub
		boolean ok = false;
		boolean saSigned = false;
		try{
			new HeronDBDao().getUserData("Dongsheng Zhu");
		}catch(Exception ex){
			
		}
		if(!saSigned)
		{
			//response.sendRedirect("system_access_agreement.jsp");
			RequestDispatcher rd = request.getRequestDispatcher("system_access_agreement.jsp");
			rd.forward(request, response);

		}
		else if(ok)
		{
			//response.sendRedirect(props.getProperty(CAS_URL));
		}
		else
		{
			response.sendRedirect(props.getProperty(CHALK_URL));
		}
	}

}
