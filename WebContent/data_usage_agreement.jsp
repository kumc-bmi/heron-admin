<%@ page import="edu.ku.biostatistics.heron.base.*" %>
<%
String val = request.getAttribute(StaticValues.VAL_MESSAGE)+""; 
String message = val!=null && !val.equals("null")?val:"";
String txtRTitle = request.getParameter("txtRTitle");
String txtRTitleDisplay = txtRTitle==null?"":txtRTitle;
String resDesc = request.getParameter("resDesc");
String resDescDisplay = (resDesc==null)?"":resDesc;
String empIds = request.getParameter("empIds");
String emplIdDisplay = empIds==null?"":empIds;
String nonempIds = request.getParameter("nonempIds");
String nonEmpIdDisplay = nonempIds==null?"":nonempIds;
String expDate = request.getParameter("expDate");
String expDateDisplay = expDate==null?"":expDate;
%>
<%@ page language="java" contentType="text/html; charset=ISO-8859-1"
    pageEncoding="ISO-8859-1"%>
<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=ISO-8859-1">
<title>data usage agreement</title>
<link href="static/kumc/kumc.css" rel="stylesheet" type="text/css"
	title="KUMC Style" />
<script type="text/javascript" language="JavaScript"
	src="static/kumc/search.js"></script>
</head>
<body>
<%@ include file="header.html" %>
	<div align="center" class="h5red"><blink><%=message%></blink></div>
	<form id="frmSponsor" action="SponsorshipServlet">
	<input type="hidden" name="spnsr_type" id="spnsr_type" value="<%=StaticValues.DATA_ACCESS %>"/>
	<p></p>
	<table>
		<tr><th colspan=2><h4>Sponsor HERON Data Usage Users</h4></th></tr>
		<tr><td>&nbsp;</td></tr>
		<tr><td><h5>Title of the Research: </h5></td><td><input type="text" name="txtRTitle" id="txtRTitle" value="<%=txtRTitleDisplay %>" size="66" maxlength="500"></td></tr>
		<tr><td><h5>Description of the Research: </h5></td><td><textarea rows="" cols="50" name="resDesc" id="resDesc"><%=resDescDisplay %></textarea></td></tr>
		<tr><td><h5>Network logon Ids of KUMC employees: </h5></td><td><input type="text" name="empIds" id="empIds" value="<%=emplIdDisplay %>" size="66" maxlength="500"><h5>(Separate by ;)</h5></td></tr>
		<tr><td><h5>Network logon Ids of non-KUMC employees: </h5></td><td><input type="text" name="nonempIds" id="nonempIds" value="<%=nonEmpIdDisplay %>" size="66" maxlength="500"><h5>(Separate by ;)</h5></td></tr>
		<tr><td><h5>Date of expiration (mm/dd/yyyy): </h5></td><td><input type="text" name="expDate" id="expDate" size="30" value="<%=expDateDisplay %>" maxlength="10"><h5>(Leave blank if requesting access until the user KUMC account is canceled or leaves KUMC)</h5></td></tr>
	</table>
	<p></p><p></p>
	
	Agreement ..........
	<h5>
	 Note: all users must have an LDAP account because they will be required to
 go through the training in Chalk.

 Here's the exact text from the data use agreement
 A.      Data Recipient agrees to use or disclose the Limited Data Set only
 for the limited purposes necessary to conduct the following research
 (enter Research Project Title and a brief description or attach a
 supplemental research protocol):

 Data Recipient certifies that the research to be conducted is in an area
 of Data Recipient’s scientific expertise and that the data request is
 limited in scope to the minimum information necessary to conduct the
 research project described above (the "Research Project").

 B.      The individuals, or classes of individuals, employed by KUMC who
 shall be permitted by Data Recipient to use or receive the Limited Data
 Set for purposes of the Research Project shall be limited to:

 The individuals not employed by KUMC who shall be permitted by Data
 Recipient to use or receive the Limited Data Set for purposes of the
 Research Project shall be limited to:


 Note: this application for sponsoring team members will reused for data
 use agreements.  The only difference for data use, will be the PI needs to
 specify the data he wants but that's probably separate from the initial
 approval.

 So we we'll want a flag on the system access sponsoring to say the
 sponsored individual is sponsored for "viewing" versus "data use".
 
 	
	 Note: all users must have an LDAP account because they will be required to
 go through the training in Chalk.

 Here's the exact text from the data use agreement
 A.      Data Recipient agrees to use or disclose the Limited Data Set only
 for the limited purposes necessary to conduct the following research
 (enter Research Project Title and a brief description or attach a
 supplemental research protocol):

 Data Recipient certifies that the research to be conducted is in an area
 of Data Recipient’s scientific expertise and that the data request is
 limited in scope to the minimum information necessary to conduct the
 research project described above (the "Research Project").

 B.      The individuals, or classes of individuals, employed by KUMC who
 shall be permitted by Data Recipient to use or receive the Limited Data
 Set for purposes of the Research Project shall be limited to:

 The individuals not employed by KUMC who shall be permitted by Data
 Recipient to use or receive the Limited Data Set for purposes of the
 Research Project shall be limited to:


 Note: this application for sponsoring team members will reused for data
 use agreements.  The only difference for data use, will be the PI needs to
 specify the data he wants but that's probably separate from the initial
 approval.

 So we we'll want a flag on the system access sponsoring to say the
 sponsored individual is sponsored for "viewing" versus "data use".
 </h5>
 <br><p></p>
<div align="center">
	<input type="submit" name="agreementbtn" id="accept" value="Accept and Submit"/><input type="submit" id="cancel" name="agreementbtn" value="Cancel"/>
</div>
<p></p>
</form>
<%@ include file="footer.html" %>
</body>
</html>