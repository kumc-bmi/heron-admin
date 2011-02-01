<%@ page import="edu.ku.biostatistics.heron.base.*" %>
<% String val = request.getAttribute(StaticValues.VAL_MESSAGE)+""; 
   String message = val!=null && !val.equals("null")?(val+" Note: Turn on Javascript for better user experience !"):"";
   String sigVal = request.getParameter("txtName");
   String sigDate = request.getParameter("txtSignDate");
   String sigValDisplay = sigVal!=null?sigVal:"";
   String sigDateDisplay = sigDate!=null?sigDate:"";
%>
<!DOCTYPE html>
<html lang="en" xmlns="http://www.w3.org/1999/xhtml">
<head>
<link rel="stylesheet" type="text/css" media="all" href="datepicker/jsDatePick_ltr.min.css" />
<script type="text/javascript" src="static/kumc/heron.js"></script>
<script type="text/javascript" src="datepicker/jsDatePick.min.1.3.js"></script>
<script type="text/javascript">
	window.onload = function(){
		new JsDatePick({
			useMode:2,
			target:"txtSignDate",
			dateFormat:"%m/%d/%Y"
			/*selectedDate:{				This is an example of what the full configuration offers.
				day:5,						For full documentation about these settings please see the full version of the code.
				month:9,
				year:2006
			},
			yearsRange:[1978,2020],
			limitToToday:false,
			cellColorScheme:"beige",
			dateFormat:"%m-%d-%Y",
			imgPath:"img/",
			weekStartDay:1*/
		});
	};
</script>
</head>
<body>

<div align="center"><blink><font color="red"><%=message%></font></blink></div>
<form id="frmSysAccess" action="SysAccessServlet">
<h3 align="center">UNIVERSITY OF KANSAS MEDICAL CENTER</h3> <p></p>
<h3 align="center">HERON SYSTEM ACCESS AGREEMENT</h3><p></p>
<h3 align="center">(PREPARATORY TO RESEARCH)</h3><p></p>

I, <u><%=request.getRemoteUser() %></u> ("System User"), acknowledge that as a condition of viewing any data component(s) from the University of Kansas Medical Center (KUMC) Healthcare Enterprise Repository for Ontological Narration ("HERON"), I must comply with the terms and conditions of this HERON System Access Agreement ("Agreement"). 

I acknowledge that violation of this Agreement will subject me to sanctions including but not limited to loss of system privileges and/or institutional disciplinary action.
<p/>
<h3>1.	SYSTEM ACCESS SCOPE AND PURPOSE</h3><p/>
System User understands that the access to the HERON system authorized by this Agreement shall be limited to the conduct of queries to view de-identified data sets, solely for purposes of conducting activities preparatory to research, and that such access may be terminated by KUMC at any time.  For purposes of this agreement, the term "de-identified"  shall have the same meaning as de-identified in 45 C.F.R. §164.514(b), and activities "preparatory to research" shall be defined as follows:  
<p/>
1.	the development of research questions; 
<p/>
2.	the determination of study feasibility (in terms of the available number and eligibility of potential study participants); and
<p></p>
3.	the development of eligibility (inclusion and exclusion) criteria
Access to other HERON data or use of HERON data for other purposes shall be permitted by KUMC only for qualified faculty and collaborating researchers specifically approved by the HERON Data Request Oversight Committee after submission of a project-specific information request, research proposal and executed data use agreement, in a format acceptable to Committee.  All forms required for access to the HERON system may be obtained from Division of Medical Informatics, Department of Biostatistics and should be submitted to the HERON Data Request Oversight Committee at least 7 days prior to the desired date of system access. 
KUMC, the University of Kansas Hospital Authority and Kansas University Physicians, Inc. disclaim all warranties as to the accuracy of the data in HERON or the acceptable performance or fitness of the data for any particular purpose.  As such, the System User acknowledges that KUMC, KUH and UKP do not and cannot warrant the results that may be obtained by viewing data included in the Data Set, and System User accepts the Data Set AS IS WITH ALL FAULTS.
<p></p>
<h3>2.	SYSTEM USER HEREBY AGREES:</h3>
<P></P>
A.	To comply with state and federal confidentiality laws, including but not limited to, the Health Insurance Portability and Accountability Act of 1996 ("HIPAA") and its implementing regulations, as amended from time to time, and to comply with KUMC privacy rules and policies and HERON system policies and procedures;
<P></P>
B.	That only System User shall be permitted to use System User’s Heron user ID and password to query the HERON system and access the resulting Data Set(s).  System User is prohibited from sharing or disclosing his/her HERON user ID and password and the Data Sets resulting from System User’s queries with other individuals or entities, except as required by law. 
<P></P>
C.	That the Data Set(s) resulting from System User’s queries shall only be viewed by System User within the HERON system/environment.  No Data Sets or data accessed by System User hereunder may be extracted from the HERON system via printing, downloading, screenshots, saving webpages or other methods. 
<P></P>
D.	To restrict individual queries to bona fide research issues preparatory to research as defined above. System User agrees not to formulate queries that could be used for competitive institutional or individual advantage of any party other than KUMC, the University of Kansas Hospital Authority, or Kansas University Physicians, Inc. 
<P></P>
E.	That the research to be conducted is in an area of his/her scientific expertise; 
<P></P>
F.	Not to identify, or attempt to identify, data contained in the Data Set(s) by any means, including using participating organization’s clinical systems (Examples: O2, EPIC, IDX, Siemens) or other information together with the Data Set (Example: voter registration records), or to contact any individual whose identity is discovered through the Data Set. 
<P></P>
G.	To report in writing to the KUMC Privacy Official at hipaa@kumc.edu any use or disclosure of protected health information (as defined in 45 C.F.R. 160.103) not covered by this Agreement that becomes known to System User, within  24 hours of its discovery.  The Data Set viewed by System User is not intended to include the following identifiers: 
Names; All geographic subdivisions smaller than a State, including street address, city, county, precinct, zip code, and their equivalent geocodes, except for the initial three digits of a zip code if, according to the current publicly available data from the Bureau of the Census: (1) The geographic unit formed by combining all zip codes with the same three initial digits contains more than 20,000 people; and (2) the initial three digits of a zip code for all such geographic units containing 20,000 or fewer people is changed to 000; All elements of dates (except year) for dates directly related to an individual, including birth date, admission date, discharge date, date of death; and all ages over 89 and all elements of dates (including year) indicative of such age, except that such ages and elements may be aggregated into a single category of age 90 or older; Telephone numbers; Fax numbers; Electronic mail addresses; Social security numbers; Medical record numbers; Health plan beneficiary numbers; Account numbers; Certificate/license numbers; Vehicle identifiers and serial numbers, including license plate numbers; Device identifiers and serial numbers; Web Universal Resource Locators (URLs); Internet Protocol (IP) address numbers; Biometric identifiers, including finger and voice prints; Full face photographic images and any comparable images; Any other unique identifying number, characteristic, or code, except as permitted by paragraph 45 C.F.R. 164.514 (c).
In the event that Data Recipient becomes aware of the inclusion in the Data Set of such an identifier, Data Recipient shall immediately report such occurrence to HERON program staff (email: phi_informatics@kumc.edu phone: 913-588-4703) and the KUMC Privacy Official, and cooperate with KUMC to address the occurrence in compliance with HIPAA.   
<P></P>
H.	To immediately destroy or return any data that System User comes into possession of that System User is not authorized to possess pursuant to the terms of this User Agreement. 
<P></P>
I.	To not use the Data Set or other information obtained from HERON to make clinical or medical decisions. 
<P></P>
J.	To not, under any circumstance, sell the Data Set, or any data obtained from HERON. 
<P></P>
<h3>3.	The University of Kansas Hospital Authority and Kansas University Physicians, Inc. are third-party beneficiaries of this Agreement and shall be entitled to enforce any obligation, responsibility or claim of KUMC pursuant to this Agreement. </h3>
<P></P>
<h3>4.	This Agreement may be amended or terminated at any time, with or without cause, by the HERON Executive Committee. </h3>
<h3>AGREED TO AND ACCEPTED BY:</h3>
<p></p>
Name: <%=session.getAttribute(StaticValues.USER_FULL_NAME) %><br>
Title: <%=session.getAttribute(StaticValues.USER_TITLE) %><p></p>
By typing my name below, I agree to the foregoing and confirm my electronic signature to this Agreement.<p></p>
System User Signature:<input type="text" maxlength="40" id="txtName" name="txtName" value="<%=sigValDisplay %>"/> Date(MM/DD/YYYY): <input type="text" name="txtSignDate" id="txtSignDate" maxlength="10" value="<%=sigDateDisplay %>" />  
<p></p>
<input type="hidden" name="accepted" id="accepted"/>
<input type="submit" name="agreementbtn" id="accept" value="Accept"/> <input type="submit" id="decline" name="agreementbtn" value="Decline"/>
<script type="text/javascript">
	document.getElementById('accept').onclick = function(){
		return doAcceptAgreement();
	};

	document.getElementById('decline').onclick = function(){
		document.getElementById("accepted").value='F';
		document.getElementById("frmSysAccess").submit();
	};
</script>
<p></p>
(Original to be filed with HERON)
(System User to retain copy for research file)
<p></p>
For further assistance email heron-admin@kumc.edu
</form>
</body>
</html>
