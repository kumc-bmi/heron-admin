<%@ page import="edu.kumc.informatics.heron.util.StaticDataUtil"%>
<%@ page import="java.util.Properties"%>
<%@ page errorPage="error_page.jsp"%>
<%
	Properties prop = StaticDataUtil.getSoleInstance().getProperties();
%>

<!DOCTYPE html>
<html lang="en" xmlns="http://www.w3.org/1999/xhtml">
<head>
<title>HERON Admin - Raven Research Portal at KUMC</title>
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
<p class="indent_half"><a href="term_heron_users.jsp">Terminate
Sponsored HERON Users</a></p>
<p class="indent_half"><a href="system_users_report.jsp">HERON
System Users Report</a></p>
<p class="indent_half"><a href="approved_users_report.jsp">HERON
Approved Users Report</a></p>
<p class="indent_half"><a href="http://bmidev1.kumc.edu/trac">TRAC</a></p>
<p class="indent_half"><a
	href="http://biostat-pts.kumc.edu/eres/jsp/kumcpr.jsp">Project
Request Form</a></p>
<p>&nbsp;</p>
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
<a href="logout.jsp">logout</a></div>
<h1>HERON Admin</h1><p></p>

<div class="kumc_middle_rows_full">
    <p>These are the HERON administrative tools.
            <em>We're in a transition from where this
            was the home page of <cite>Raven</cite>,
            the Medical Informatics research portal at KUMC.</em></p>
    <p>
        We also provide the following tools:
    </p>
<ul>
	<li><a href="http://biostatistics.kumc.edu/bio_proj_cris.shtml">CRIS</a>:
	a Comprehensive Research Information System</li>
	<li><a href="https://redcap.kumc.edu/">REDCap</a>:
	 a web-based application to support case report form data capture for research studies 
	</li>
	<li><a href="AuthServlet">HERON</a>: (Healthcare Enterprise Repository for Ontological Narration)
 allows you to explore deidentified data from Epic/O2 (the electronic
 medical record) and soon, IDX (the clinical billing system).
	</li>
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
<div align="center">
<h2>Meet the KUMC Informatics Team</h2>
<img src="static/KUMCInformatics.jpg" width="450" height="270"
	alt="KUMC Informatics Team" />
<br />Seated: Russ, Dan and Arvinder; Standing: Dongsheng, Angelica, Cathy,
Bhargav, and Kahlia
</div>
</div>
</div>

<!-- end middle rows--> <!--  End Editable  -->
</div>
</div>
</div>
</div>
<br clear="all" />

<p>
    <small>build number: <%=prop.getProperty("scm.version").substring(0, 12)%></small>
</p>

<%@ include file="footer.html"%>
</body>
</html>