package edu.ku.biostatistics.heron.servlet;

import java.io.IOException;
import java.util.Properties;

import javax.servlet.ServletException;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

import edu.ku.biostatistics.heron.util.StaticDataUtil;
import static edu.ku.biostatistics.heron.base.StaticValues.*;

/**
 * Servlet implementation class SysAccessServlet
 */
public class SysAccessServlet extends HttpServlet {
	private static final long serialVersionUID = 1L;
	private Properties props = StaticDataUtil.getSoleInstance().getProperties();    
    /**
     * @see HttpServlet#HttpServlet()
     */
    public SysAccessServlet() {
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
		String type = request.getParameter("accepted");
		if("T".equals(type))
		{
			response.sendRedirect(props.getProperty(I2B2_CLIENT_SERVICE));
		}
		else
		{
			response.sendRedirect("http://www.kumc.edu/");
		}
	}

}
