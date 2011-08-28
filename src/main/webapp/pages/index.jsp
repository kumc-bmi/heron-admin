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

  <jsp:directive.page contentType="text/html; charset=utf-8"
                      pageEncoding="utf-8"/>
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
        <!-- TODO: this is known at build time; no need to compute it at runtime. -->
        <jsp:element name="meta">
          <jsp:attribute name="name">build-number</jsp:attribute>
          <jsp:attribute name="content">
                  <jsp:expression>
                    prop.getProperty("scm.version").substring(0, 12)
                  </jsp:expression>
          </jsp:attribute>
        </jsp:element>
          <style type="text/css">
            .photo {text-align: center; margin-bottom: 1em }
          </style>
      </head>
      <body>
        <div id="menu">
          <ul>
            <li><a href="AuthServlet">HERON i2b2 Query and Analysis Tool</a>
            </li>
            <li><a href="SponsorshipServlet?init_type=VIEW_ONLY">HERON
                Sponsorship Request</a>
            </li>
            <li><a href="SponsorshipServlet?init_type=DATA_ACCESS">HERON
                Data Usage Request</a>
            </li>
            <li><a href="droctools.jspx">DROC Oversight Tools</a></li>
            <li><a
                href="http://biostat-pts.kumc.edu/eres/jsp/kumcpr.jsp"
                >Biostatistics Department Project Request Form</a>
            </li>
          </ul>
        </div>

        <div id="main">
          <div id="heron-tricol-01" class="photo">
            <img src="static/220px-Heron_tricol_01.JPG" alt=""/>
          </div>

          <h1>HERON Research Data Repository</h1>

          <!-- TODO: why does this para turn blue? -->
          <p>HERON (Healthcare Enterprise Repository for Ontological Narration)
            allows you to explore de-identified data from Epic/O2 (the
            hospital electronic medical records) and IDX (the clinical billing
            system).
          </p>

          <p>The <a href="AuthServlet">HERON i2b2 Query and Analysis Tool</a>
            is the main tool for composing queries such as "how many patients
            in the repository have been diagnosed with diabetes and live within
            20 miles of the KUMC campus?"</p>

          <p>Access to de-identified data is non-human subjects research and
            does not require IRB approval. For qualified faculty who want
            <em>view-only</em> access to do patient count queries, executing
            a system access agreement is the only requirement.</p>

          <p><a href=
                "http://informatics.kumc.edu/work/wiki/HERONTrainingMaterials"
                >Getting Access to HERON</a> explains the process in detail.
          </p>

          <p>A Data Request Oversight Committee (DROC) oversees requests to:</p>
          <ul>
            <li><a href="SponsorshipServlet?init_type=VIEW_ONLY">sponsor
                collaborators and research team members</a></li>

                <li><a href="SponsorshipServlet?init_type=DATA_ACCESS">extract
                    data sets</a></li>
          </ul>

          <p>The
            <a href=
               "http://informatics.kumc.edu/work/blog/2011/07/first-clinic"
               >Frontiers Clinical/Translational Informatics Clinic</a>
            meets every other Tuesday
            for investigators needing assistance using informatics tools
            for data exploration, cohort discovery, and data collection.
            The clinic is a brainstorming session and an education forum for
            investigators and informatics to share knowledge, provide feedback,
            and optimize the use of systems.</p>

          <p>To set up consultation regarding your project, complete a
            <a href="http://biostat-pts.kumc.edu/eres/jsp/kumcpr.jsp"
               >Biostatistics Department Project Request Form</a>.
          </p>

          <p><small><a href="#heron-tricol-01">photo</a> credit:
              <a href="http://commons.wikimedia.org/wiki/User:Chrharshaw"
                 >Christopher Harshaw</a></small>
          </p>

        </div>

        <div id="rightnav">
          <div>
            <b id="user-id">
              <jsp:expression>request.getRemoteUser()</jsp:expression></b>
          </div>
        </div>

      </body>
    </html>
  </x:transform>
</jsp:root>
