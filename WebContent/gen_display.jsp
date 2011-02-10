<%@ page import="edu.kumc.informatics.heron.base.*" %>
<%@ page language="java" contentType="text/html; charset=ISO-8859-1"
    pageEncoding="ISO-8859-1"%>
<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=ISO-8859-1">
<title>Insert title here</title>
<link href="static/kumc/kumc.css" rel="stylesheet" type="text/css"
	title="KUMC Style" />
<script type="text/javascript" language="JavaScript"
	src="static/kumc/search.js"></script>
</head>
<body>
<%@ include file="header.html" %>
	<p></p>
	<div class="h5red">
	<%= request.getAttribute(StaticValues.VAL_MESSAGE) %>
	</div>
<%@ include file="footer.html" %>
</body>
</html>