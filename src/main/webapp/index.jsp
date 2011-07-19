<jsp:root version="2.1"
          xmlns:jsp="http://java.sun.com/JSP/Page"
          xmlns:c="http://java.sun.com/jsp/jstl/core"
          xmlns:x="http://java.sun.com/jsp/jstl/xml">
  <!--
  aha!
  the right XML NS URI is given in
  http://download.oracle.com/javaee/5/jstl/1.1/docs/tlddocs/x/tld-summary.html
  I was really struggling with:
  org.apache.jasper.JasperException: /index.jsp(14,31) According to TLD or attribute directive in tag file, attribute xslt does not accept any expressions
  -->

  <jsp:directive.page contentType="text/html" pageEncoding="utf-8"/>
  <jsp:directive.page import="edu.kumc.informatics.heron.util.StaticDataUtil" />
  <jsp:directive.page import="java.util.Properties" />
  <!-- TODO: restore <jsp:directive.page errorPage="error_page.jsp" /> -->
  <jsp:scriptlet>
                Properties prop = StaticDataUtil.getSoleInstance().getProperties();
  </jsp:scriptlet>

  <c:import var="layout" url="kumc_layout.xml"/>
  <x:transform xslt="${layout}">
    <html lang="en"
          xmlns="http://www.w3.org/1999/xhtml">
      <head>
        <title>HERON Research Data Repository</title>
      </head>
      <body>
        <div id="menu">
          <ul>
            <li><a
                href="http://biostat-pts.kumc.edu/eres/jsp/kumcpr.jsp">Biostatistics
	Department Project Request Form</a></li>

            <li><a href="SponsorshipServlet?init_type=VIEW_ONLY">HERON
                Sponsoring</a></li>
            <li><a href="SponsorshipServlet?init_type=DATA_ACCESS">HERON
                Data Usage</a></li>
          </ul>
        </div>

        <div id="main">
          <h1>HERON Research Data Repository</h1>
          <p><a href="AuthServlet">HERON i2b2 Query and Analysis Tool</a></p>

      <div class="photo">
	<img src="static/220px-Heron_tricol_01.JPG" alt=""/>
        <address>photo credit: <a href="http://commons.wikimedia.org/wiki/User:Chrharshaw">Christopher Harshaw</a></address>
      </div>

          <hr />
          <p><a href="approve_sponsorship.jsp">Approve
              Sponsored HERON Users</a></p>
          <p><a href="term_heron_users.jsp">Terminate
              Sponsored HERON Users</a></p>
          <p><a href="system_users_report.jsp">HERON
              System Users Report</a></p>
          <p><a href="approved_users_report.jsp">HERON
              Approved Users Report</a></p>

          <hr />

        </div>
        <div id="rightnav">
          <div class="span-5 last">
            <div id="login" align="right">Welcome <jsp:expression>request.getRemoteUser()</jsp:expression>
              <a href="logout.jsp">logout</a><!-- TODO: use POST to logout -->
            </div>
              <hr />
              @@feedback survey
              <hr />
              Ideas? Problems? Questions? Contact us at <a
                href="mailto:heron-admin@kumc.edu">heron-admin@kumc.edu</a>.
                <small>build number: <jsp:expression>prop.getProperty("scm.version").substring(0, 12)</jsp:expression></small>
          </div>
        </div>

      </body>
    </html>
  </x:transform>
</jsp:root>
