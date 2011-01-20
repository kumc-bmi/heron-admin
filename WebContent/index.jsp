<%@ page import="edu.ku.biostatistics.heron.util.*" %> 
<%@ page import="edu.ku.biostatistics.heron.base.*" %>
<%@ page import="java.util.*" %> 
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
<%@ include file="header.html" %>

<div id="kumc_frame"><!-- ***************************************** Navigation ***************************************** -->
<div id="kumc_contentleft">

<div id="kumc_leftlinks"><!--insert an include file for your left hand navigation links here,
	the file will look something like the code below-->
<p>Biomedical Informatics Services</p>
<p class="indent_half"><a
	href="http://biostatistics.kumc.edu/bio_proj_cris.shtml">CRIS</a></p>
<p class="indent_half"><a href="AuthServlet">HERON</a></p>
<p class="indent_half"><a href="sponsorship.jsp">HERON Sponsoring</a></p>
<p class="indent_half"><a href="data_usage_agreement.jsp">HERON Data Usage</a></p>
<p class="indent_half"><a href="approve_sponsorship.jsp">Approve Sponsored HERON Users</a></p>
<p class="indent_half"><a href="http://bmidev1.kumc.edu/trac">trac</a></p>
<p class="indent_half"><a
	href="http://biostat-pts.kumc.edu/eres/jsp/kumcpr.jsp">project
request form</a></p>
<p></p>
<p>Also at KU</p>
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




<!-- below crumb trail is optional -->
<div class="kumc_crumbtrail"><a
	href="http://biostatistics.kumc.edu/">Biostatistics Department</a></div>
<div id="login" align="right">Welcome <%=request.getRemoteUser() %> <a
	href="https://cas.kumc.edu/cas/logout">logout</a> </div>


<h1>Raven Research Portal</h1>

<div id="kumc_feature_text">
<div class="kumc_middle_rows_full">
<p>Welcome to <dfn>Raven</dfn>, the Biomedical Informatics Portal at
KUMC. Raven's goal is to collect tools for translational research and
connect informatics to our customers.</p>
</div>
</div>

<div id="kumc_middle_rows_full">
<div class="kumc_mr_row_full">
<p>Currently, we provide 3 tools:</p>
<ul>
	<li><a href="http://biostatistics.kumc.edu/bio_proj_cris.shtml">CRIS</a>:
	a Comprehensive Research Information System</li>
	<li><a href="<%=prop.getProperty(StaticValues.CAS_LOGIN_URL)%>?service=<%=prop.getProperty(StaticValues.I2B2_CLIENT_SERVICE) %>">HICTR / i2b2</a>: the
	HICTR participant registry accessed through <a
		href="http://www.i2b2.org">i2b2</a></li>
	<li><a href="http://bmidev1.kumc.edu/trac">trac</a>: our current
	development process</li>
</ul>

<p>Ideas? Problems? Questions? Contact us at <a
	href="mailto:heron-admin@kumc.edu">heron-admin@kumc.edu</a>.</p>


<p>If you have a project request, please use our convenient <a
	href="http://biostat-pts.kumc.edu/eres/jsp/kumcpr.jsp">project
request form</a>.</p>

<p>Why "raven"? The raven is this website's inspirational mascot.
Ravens, the largest of the <a
	href="http://en.wikipedia.org/wiki/Corvidae">corvids</a>, and are known
for their intelligence and predisposition to collect things.</p>

<h2>Meet the KUMC Informatics Team</h2>

<p>These services are provided by the KUMC Informatics Team:</p>

<img src="static/KUMCInformatics.jpg" width="609"
	alt="KUMC Informatics Team" />
<p>Seated: Russ and Angelica; Standing: Venkata, Arvinder, Dan,
Rick, Cathy, Kahlia</p>

<p>See also <a
	href="http://biostatistics.kumc.edu/bio_staff.shtml#c">contact
information.</a></p>

</div>
</div>
<div id="kumc_middle_rows_full">
<div class="kumc_greyline"><a href="#top" title="to top of page">top
of page</a></div>
</div>



<!-- end middle rows--> <!--  End Editable  --></div>
</div>
</div>
</div>
</div>
<br clear="all" />

<%@ include file="footer.html" %>
</div>
</div>
</body>
</html>