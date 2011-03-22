<%@ page import="edu.kumc.informatics.heron.base.*" %>
<%@ page import="edu.kumc.informatics.heron.util.*" %>

<div align="center">
<p><b>We have made significant changes to the HERON repository which you need to review. <br>
Please review the changes carefully before proceeding to use the system.</b>
</p>

<iframe src="<%= new GuiUtil().getRecentDisclaimer() %>" width="1000" height="700">
<a href="http://informatics.kumc.edu/work/wiki/HERONDisclaimerMarch8">you are using a very old browser.
Click here to go directly to included content.</a>
</iframe>
</div>
<br>
<form action="AcknowledgeDisclaimerServlet">
<div align="center">
	<b>I have reviewed the changes:</b>
	<input type="submit" name="submitbtn" id="accept" value="Acknowledge"/><input type="submit" id="cancel" name="submitbtn" value="Cancel"/>
</div>
<p></p>
</form>
</form>