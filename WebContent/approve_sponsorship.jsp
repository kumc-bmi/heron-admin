<%@ page import="edu.ku.biostatistics.heron.base.*" %>
<%@ page import="edu.ku.biostatistics.heron.util.*" %>
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
<title>sponsor users</title>
<link href="static/kumc/kumc.css" rel="stylesheet" type="text/css"
	title="KUMC Style" />
<link href="static/kumc/heron.css" rel="stylesheet" type="text/css"
	title="heron Style" />
<script type="text/javascript" language="JavaScript"
	src="static/kumc/search.js"></script>
<style type="text/css">
table.heron {
	border: 1px inset #8B8378;
	-moz-border-radius: 1px;
}

table.heron td {
	border: 1px solid black;
	padding: 0.2em 2ex 0.2em 2ex;
	color: black;
}

table.heron tr.d0 td {
	background-color: #FCF6CF;
}

table.heron tr.d1 td {
	background-color: #FEFEF2;
}
</style>
</head>
<body>

<%@ include file="header.html" %>
	<div align="center" class="h5red"><blink><%=message%></blink></div>
	<form id="frmSponsor" action="SponsorshipApprovalServlet">
	<input type="hidden" name="spnsr_type" value="<%=StaticValues.VIEW_ONLY %>"/>
	<p></p>
	<%= new GuiUtil().getSponsorship("VIEW_ONLY",request.getRemoteUser()) %>
	<p></p>
	<p></p>
<div align="center">
	<input type="submit" name="submitbtn" id="accept" value="Submit"/><input type="submit" id="cancel" name="submitbtn" value="Cancel"/>
</div>
<p></p>
</form>
<%@ include file="footer.html" %>
</body>
</html>