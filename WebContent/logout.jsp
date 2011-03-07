<%
 	session.invalidate();
	response.sendRedirect("https://cas.kumc.edu/cas/logout");
%>