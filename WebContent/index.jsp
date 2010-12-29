<%@ page import="edu.ku.biostatistics.heron.util.*" %> 
<%@ page import="edu.ku.biostatistics.heron.base.*" %>
<%@ page import="java.util.*" %> 
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
<div id="kumc_accessibilty_skip"><a href="#maincontent" name="top"><img
	src="static/kumc/spacer.gif" alt="Skip redundant pieces" width="1"
	height="1" border="0" /></a></div>
<div id="kumc_container"><!--  Header -->
<div id="kumc_intro">
<div id="kumc_topmostheader">
<div id="kumc_header_links"><a href="http://www.ku.edu/"
	title="University of Kansas">KU</a>&#160; |&#160; <a
	href="http://www.kumc.edu/" title="University of Kansas Medical Center"
	class="kumc_homelink">Medical Center</a>&#160;</div>
<div id="kumc_header_logo"><a href="http://www.kumc.edu/"><img
	src="static/kumc/masthead_logo.gif"
	alt="The University of Kansas Medical Center"
	title="The University of Kansas Medical Center" hspace="0" vspace="0"
	width="143" height="53" align="right" border="0" /></a></div>
</div>
<div id="kumc_topbar"></div>

<div id="kumc_titlebar">
<div id="kumc_kuaffiliation">Biostatistics Department</div>
<div id="kumc_searchbar">
<div id="kumc_searchform" align="right">
<form class="search" method="get"
	action="http://www.kumc.edu/cgi-bin/advsearch">
<div><label for="searchtype" accesskey="S"> <select
	name="location" id="searchtype">
	<option value="1" selected="selected">Search KUMC web site</option>
	<option value="23">Search phone directory</option>
</select></label><label for="searchtext" accesskey="I"><input id="searchtext"
	name="search" size="11" alt="enter search terms"
	class="kumc_searchform input" value="keyword/name "
	onfocus="this.value='';" /></label>&#160;<input class="kumc_searchbutton"
	name="Search" type="image" src="static/kumc/searcharrow.gif"
	alt="Search" /></div>
</form>
</div>
</div>
</div>

</div>
<div id="kumc_frame"><!-- ***************************************** Navigation ***************************************** -->
<div id="kumc_contentleft">

<div id="kumc_leftlinks"><!--insert an include file for your left hand navigation links here,
	the file will look something like the code below-->
<p>Biomedical Informatics Services</p>
<p class="indent_half"><a
	href="http://biostatistics.kumc.edu/bio_proj_cris.shtml">CRIS</a></p>
<p class="indent_half"><a href="/raven/AuthServlet">HERON</a></p>
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

<!--  Footer  -->

<div id="kumc_footercontainer">
<div id="kumc_contentbottom"></div>
<div id="kumc_footer">
<div id="kumc_footerframe">
<div id="kumc_contactinfo">
<div style="padding-bottom: 3px;"><a
	href="http://www.kumc.edu/Pulse/howtocontact.html"
	class="kumc_grey_u_link">Contact Us</a><br />
</div>
<address>The University of Kansas<br />
Medical Center<br />
3901 Rainbow Boulevard<br />
Kansas City, KS 66160<br />
913-588-5000<br />
913-588-7963 TDD</address>
</div>

<div id="kumc_copyright"><img class="kumc_jayhawk"
	src="static/kumc/footer_jayhawk.gif" border="0" align="right"
	hspace="0" vspace="0" alt="KU Jayhawk" title="KU Jayhawk" height="37"
	width="37" />&#160;<a href="http://www.kumc.edu/Pulse/copyright.html"
	class="kumc_grey_u_link">&#169; <script language="JavaScript"
	type="text/javascript">
	var d = new Date();
	yr = d.getFullYear();
	if (yr != 1863)
		document.write(yr);
</script> </a>&#160;The University of Kansas Medical Center<br />
<a href="http://www.kumc.edu/Pulse/aboutthissite.html"
	title="About the University of Kansas Medical Center web site"
	class="kumc_grey_u_link">About this Site</a>&#160;|&#160;<a
	href="http://www.kumc.edu/Pulse/eo_statement.html"
	title="The University of Kansas Medical Center's Equal Opportunity Statement"
	class="kumc_grey_u_link">An EO/AA/Title IX Institution</a>&#160;|&#160;<a
	href="http://www.kumc.edu/Pulse/privacy.html"
	title="The University of Kansas Medical Center's Privacy Statement"
	class="kumc_grey_u_link">Privacy Statement</a>&#160;|&#160;<a
	href="http://www2.kumc.edu/directory/KUMCSiteIndex.aspx?Id=ALL"
	title="Index of University of Kansas Medical Center web sites"
	class="kumc_grey_u_link">Site Index</a>&#160;|&#160;<a
	href="http://www.kumc.edu/Pulse/help.html"
	title="Help using this web site and general KUMC campus assistance"
	class="kumc_grey_u_link">Help</a></div>

</div>
</div>
</div>
</body>
</html>