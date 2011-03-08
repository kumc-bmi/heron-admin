<%@ page import="edu.kumc.informatics.heron.base.*" %>
<%@ page import="edu.kumc.informatics.heron.util.*" %>

<div align="center">
<%= new GuiUtil().getRecentDisclaimer() %>
</div>
<p>&nbsp;</p>
<form action="AcknowledgeDisclaimerServlet">
<div align="center">
	<input type="submit" name="submitbtn" id="accept" value="Acknowledge"/><input type="submit" id="cancel" name="submitbtn" value="Cancel"/>
</div>
<p></p>
</form>
</form>