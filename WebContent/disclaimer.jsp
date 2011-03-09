<%@ page import="edu.kumc.informatics.heron.base.*" %>
<%@ page import="edu.kumc.informatics.heron.util.*" %>

<div align="center">
<iframe src="<%= new GuiUtil().getRecentDisclaimer() %>" width="800" height="600">
<a href="http://informatics.kumc.edu/work/wiki/HERONDisclaimerMarch8">you are using a very old browser.
Click here to go directly to included content.</a>
</iframe>
</div>
<p>&nbsp;</p>
<form action="AcknowledgeDisclaimerServlet">
<div align="center">
	<input type="submit" name="submitbtn" id="accept" value="Acknowledge"/><input type="submit" id="cancel" name="submitbtn" value="Cancel"/>
</div>
<p></p>
</form>
</form>