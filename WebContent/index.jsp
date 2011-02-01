<%@ page import="edu.ku.biostatistics.heron.util.*"%>
<%@ page import="edu.ku.biostatistics.heron.base.*"%>
<%@ page import="java.util.*"%>
<%@ page errorPage="error_page.jsp"%>
<%
	Properties prop = StaticDataUtil.getSoleInstance().getProperties();
%>

<!DOCTYPE html>
<html lang="en" xmlns="http://www.w3.org/1999/xhtml">
<head>
<!--	<meta name="keywords" content="add keywords" />
	<meta name="description" content="Add description of page. " />	
-->
<title>Raven Research Portal at KUMC</title>
<link href="static/kumc/kumc.css" rel="stylesheet" type="text/css"
	title="KUMC Style" />
<script type="text/javascript" language="JavaScript"
	src="static/kumc/search.js"></script>

</head>
<body>
<%@ include file="header.html"%>

<div id="kumc_frame"><!-- ***************************************** Navigation ***************************************** -->
<div id="kumc_contentleft">

<div id="kumc_leftlinks_bc"><!--insert an include file for your left hand navigation links here,
	the file will look something like the code below-->
<p><h4>Biomedical Informatics Services</h4></p>
<p class="indent_half"><a
	href="http://biostatistics.kumc.edu/bio_proj_cris.shtml">CRIS</a></p>
<p class="indent_half"><a
	href="https://redcap.kumc.edu/">REDCap</a></p>
<p class="indent_half"><a href="AuthServlet">HERON</a></p>
<p class="indent_half"><a href="SponsorshipServlet?init_type=VIEW_ONLY">HERON
Sponsoring</a></p>
<p class="indent_half"><a href="SponsorshipServlet?init_type=DATA_ACCESS">HERON
Data Usage</a></p>
<p class="indent_half"><a href="approve_sponsorship.jsp">Approve
Sponsored HERON Users</a></p>
<p class="indent_half"><a href="system_users_report.jsp">HERON
System Users Report</a></p>
<p class="indent_half"><a href="approved_users_report.jsp">HERON
Approved Users Report</a></p>
<p class="indent_half"><a href="http://bmidev1.kumc.edu/trac">TRAC</a></p>
<p class="indent_half"><a
	href="http://biostat-pts.kumc.edu/eres/jsp/kumcpr.jsp">Project
Request Form</a></p>
<p></p>
<p></p>
<p><h4>Also at KU</h4></p>
<p class="indent_half"><a
	href="http://www2.kumc.edu/healthinformatics/">Center for Health
Informatics at the University of Kansas Medical Center</a></p>
<p class="indent_half"><a href="http://biostatistics.kumc.edu/">Department
of Biostatistics</a></p>
<p class="indent_half"><a href="http://www.bioinformatics.ku.edu/">Center
for Bioinformatics at the University of Kansas Lawrence</a></p>
<p class="indent_half"><a
	href="http://www.kumc.edu/kinbre/bioinformatics.html">K-INBRE
Bioinformatics core</a></p>
<p class="indent_half"><a
	href="http://www.ittc.ku.edu/bioinformatics/">Bioinformatics and
Computational Life Science Lab in the School of Engineering at the
University of Kansas Lawrence</a></p>
<p class="indent_half"><a
	href="http://www2.kumc.edu/siddrc/bioinformatics/">Bioinformatics
resources at the University of Kansas Medical Center</a></p>
<p class="indent_half"><a
	href="http://specify5.specifysoftware.org/Informatics/?q=Informatics">Biodiversity
Informatics at Kansas</a></p>
</div>
</div>
<div id="kumc_container_nav"><!-- ***************************************** Main Content ***************************************** -->
<div id="kumc_contentcenter">
<div id="kumc_maincontent"><a name="maincontent"></a> <!-- ***************************************** Begin Editable ***************************************** -->
<div id="kumc_feature_text2">
<!-- below crumb trail is optional -->
<div id="login" align="right">Welcome <%=request.getRemoteUser()%>
<a href="https://cas.kumc.edu/cas/logout">logout</a></div>

<h1>Raven Research Portal</h1><p></p>

<div class="kumc_middle_rows_full">
Welcome to <dfn>Raven</dfn>, the Biomedical Informatics Portal at
KUMC. Raven's goal is to collect tools for translational research and
connect informatics to our customers.
<br><br>
Currently, we provide the following tools:
<ul>
	<li><a href="http://biostatistics.kumc.edu/bio_proj_cris.shtml">CRIS</a>:
	a Comprehensive Research Information System</li>
	<li><a href="https://redcap.kumc.edu/">REDCap</a>:
	 a web-based application to support case report form data capture for research studies 
	</li>
	<li><a href="AuthServlet">HERON</a>: the HICTR participant
	registry accessed through <a href="http://www.i2b2.org">i2b2</a></li>
	<li><a href="http://bmidev1.kumc.edu/trac">TRAC</a>: our current
	development process</li>
</ul>
</div>
</div>
<div id="kumc_middle_rows_full">
<div class="kumc_mr_row_full">
Ideas? Problems? Questions? Contact us at <a
	href="mailto:heron-admin@kumc.edu">heron-admin@kumc.edu</a>. Check
<a href="http://biostatistics.kumc.edu/bio_staff.shtml#c">Other contact information</a>
<p>If you have a project request, please use our convenient <a
	href="http://biostat-pts.kumc.edu/eres/jsp/kumcpr.jsp">project
request form</a>.</p>

<p>Why "raven"? The raven is this website's inspirational mascot.
Ravens, the largest of the <a
	href="http://en.wikipedia.org/wiki/Corvidae">corvids</a>, and are known
for their intelligence and predisposition to collect things.</p>

<h2>Meet the KUMC Informatics Team</h2>
<img src="static/KUMCInformatics.jpg" width="609" height="250"
	alt="KUMC Informatics Team" />
<br>Seated: Russ and Angelica; Standing: Venkata, Arvinder, Dan,
Rick, Cathy, Kahlia

</div>
</div>

<!-- end middle rows--> <!--  End Editable  -->
</div>
</div>
</div>
</div>
<br clear="all" />

<%@ include file="footer.html"%>
</body>
</html>