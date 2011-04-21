<%@ page import="edu.kumc.informatics.heron.base.*" %>
<%@ page import="edu.kumc.informatics.heron.util.*" %>
<%
String val = request.getAttribute(StaticValues.VAL_MESSAGE)+""; 
String message = val!=null && !val.equals("null")?val:"";

%>
<%@ page language="java" contentType="text/html; charset=ISO-8859-1"
    pageEncoding="ISO-8859-1"%>
<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=ISO-8859-1">
<title>terminate users</title>
<link href="static/kumc/kumc.css" rel="stylesheet" type="text/css"
	title="KUMC Style" />
<script type="text/javascript" language="JavaScript"
	src="static/kumc/search.js"></script>
<style type="text/css">
<!--
  @import url(static/kumc/heron.css);
-->
</style>
</head>
<body>

<%@ include file="header.html" %>
<div align="center" class="h5red"><blink><%=message%></blink></div>
<form id="frmTerm" action="TerminateUsers">
	<div align="center"><h4>Terminate HERON System Usage Users</h4></div>
	<p>&nbsp;</p><div align="center">
	<%= new GuiUtil().getActiveHeronUsers(session,request.getRemoteUser()) %>
	</div>
	<p>&nbsp;</p>
	<div align="center">
		<input type="submit" name="submitbtn" id="accept" value="Submit"/><input type="submit" id="cancel" name="submitbtn" value="Cancel"/>
	</div>
	<p>&nbsp;</p>
</form>
<%@ include file="footer.html" %>
</body>
</html>