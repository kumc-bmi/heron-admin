<%@ page import="edu.kumc.informatics.heron.base.*" %>
<%@ page import ="edu.kumc.informatics.heron.util.*" %>
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
String uname = session.getAttribute(StaticValues.USER_FULL_NAME)+"";
if(uname.equals("null")){
	uname = new LdapUtil().getUserInfo(request.getRemoteUser())[0];
	session.setAttribute(StaticValues.USER_FULL_NAME,uname);
}
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
<script type="text/javascript" language="JavaScript"
	src="static/kumc/search.js"></script>
</head>
<body>
<%@ include file="header.html" %>
	<div align="center" class="h5red"><blink><%=message%></blink></div>
	<form id="frmSponsor" action="SponsorshipServlet">
	<input type="hidden" name="spnsr_type" value="<%=StaticValues.VIEW_ONLY %>"/>
	<p></p>
	<table>
		<tr><th colspan=2><h4>Sponsor Heron System Usage Users</h4></th></tr>
		<tr><td>&nbsp;</td></tr>
		<tr><td><h5>Title of the General Research Area: </h5></td><td><input type="text" name="txtRTitle" id="txtRTitle" value="<%=txtRTitleDisplay %>" size="66" maxlength="500"></td></tr>
		<tr><td><h5>Description of the Preparatory to Research Activities: </h5></td><td><textarea rows="" cols="50" name="resDesc" id="resDesc"><%=resDescDisplay %></textarea></td></tr>
		<tr><td><h5>A. Network logon Ids of KUMC employees: </h5></td><td><input type="text" name="empIds" id="empIds" value="<%=emplIdDisplay %>" size="66" maxlength="500"><h5>(Separate by ;)</h5></td></tr>
		<tr><td><h5>B. Network logon Ids of <A HREF = "#affiliation">non-KUMC employees*</A>: </h5></td><td><input type="text" name="nonempIds" id="nonempIds" value="<%=nonEmpIdDisplay %>" size="66" maxlength="500"><h5>(Separate usernames by ; and put affilations in [].  <BR> For example: <b>rwaitman;dconnolly</b> <BR><b>fsmith;lhargrove[Computer Science Professor at University of Kansas-Lawrence];afranks[Analyst at HCA Lee's Summit Medical Center]</B> )</h5></td></tr>
		<tr><td><h5>Date of expiration (mm/dd/yyyy): </h5></td><td><input type="text" name="expDate" id="expDate" size="30" value="<%=expDateDisplay %>" maxlength="10"><h5>(Leave blank if requesting access until the user KUMC account is canceled or leaves KUMC)</h5></td></tr>
	</table>
	<p></p>
<P ID=affiliation>
* For non-KUMC employees, include the position and employer for any students or staff who employed by another institution where there may need to be clarification regarding conflict of interest or competitive concerns between their parent institution and KUMC, KUH or UKP.
</P>	
	<h5>
	The individuals identified in sections A and B above shall be referred to hereinafter as the Sponsor's "Research Team Members".  They will be required to individually sign a HERON System Access Agreement reinforcing their responsibilities when using HERON for prepraratory to research activities.  
 <p></p>
I <%=uname %>, will be responsible for my research team members and hereby agrees:
 <p></p>
A.    To comply with state and federal confidentiality laws, including but not limited to, the Health Insurance Portability and Accountability Act of 1996 ("HIPAA"") and its implementing regulations, as amended from time to time, and to comply with KUMC privacy rules and policies and HERON system policies and procedures;
<p></p>
B.     To reinforce to my research team members that they are prohibited from sharing or disclosing his/her HERON user ID and password and the Data Sets resulting from System User's queries with other individuals or entities, except as required by law. 
<p></p>
C.     That the Data Set(s) resulting from System User's queries shall only be viewed by System User within the HERON system/environment.  No Data Sets or data accessed by System User hereunder may be extracted from the HERON system via printing, downloading, screenshots, saving webpages or other methods. 
<p></p>
D.    My research team members will restrict individual queries to bona fide research issues preparatory to research. My team research members will not formulate queries that could be used for competitive institutional or individual advantage of any party other than KUMC, the University of Kansas Hospital Authority, or Kansas University Physicians, Inc. 
<p></p>
E.     That the research to be conducted is in an area of my research team members' scientific expertise; 
<p></p>
F.      Not to identify, or attempt to identify, data contained in the Data Set(s) by any means, including using participating organization's clinical systems (Examples: O2, EPIC, IDX, Siemens) or other information together with the Data Set (Example: voter registration records), or to contact any individual whose identity is discovered through the Data Set. 

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