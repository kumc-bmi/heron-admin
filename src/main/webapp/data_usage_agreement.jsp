<%@ page import="edu.kumc.informatics.heron.base.*"%>
<%@ page import="edu.kumc.informatics.heron.util.*"%>
<%
	String val = request.getAttribute(StaticValues.VAL_MESSAGE) + "";
	String message = val != null && !val.equals("null") ? val : "";
	String txtRTitle = request.getParameter("txtRTitle");
	String txtRTitleDisplay = txtRTitle == null ? "" : txtRTitle;
	String resDesc = request.getParameter("resDesc");
	String resDescDisplay = (resDesc == null) ? "" : resDesc;
	String empIds = request.getParameter("empIds");
	String emplIdDisplay = empIds == null ? "" : empIds;
	String nonempIds = request.getParameter("nonempIds");
	String nonEmpIdDisplay = nonempIds == null ? "" : nonempIds;
	String expDate = request.getParameter("expDate");
	String expDateDisplay = expDate == null ? "" : expDate;
	String uName = session.getAttribute(StaticValues.USER_FULL_NAME)+ "";
	String uTitle = session.getAttribute(StaticValues.USER_TITLE)+ "";
	
	if (uName.equals("null")||uTitle.equals("null")) {
		String[] info = new LdapUtil().getUserInfo(request.getRemoteUser());
		uName = info[0];
		uTitle = info[2];
		session.setAttribute(StaticValues.USER_FULL_NAME, uName);
		session.setAttribute(StaticValues.USER_TITLE, uTitle);
	}
	String sigVal = request.getParameter("txtName");
	String sigDate = request.getParameter("txtSignDate");
	String sigValDisplay = sigVal!=null?sigVal:"";
	String sigDateDisplay = sigDate!=null?sigDate:"";
%>
<%@ page language="java" contentType="text/html; charset=ISO-8859-1"
	pageEncoding="ISO-8859-1"%>
<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=ISO-8859-1">
<title>data usage agreement</title>
<link href="static/kumc/kumc.css" rel="stylesheet" type="text/css"
	title="KUMC Style" />
<script type="text/javascript" language="JavaScript"
	src="static/kumc/search.js"></script>
</head>
<body>
<%@ include file="header.html"%>
<div align="center" class="h5red"><blink><%=message%></blink></div>
<form id="frmSponsor" action="SponsorshipServlet"><input
	type="hidden" name="spnsr_type" id="spnsr_type"
	value="<%=StaticValues.DATA_ACCESS%>" />

<h4>UNIVERSITY OF KANSAS MEDICAL CENTER HERON DATA USE AGREEMENT</h4>
<p></p><p></p>
<h5>I, <%=uName%> ("I" or "Data Recipient"), acknowledge that as a
condition of receiving and using any data component(s) from the
University of Kansas Medical Center (KUMC) Healthcare Enterprise
Repository for Ontological Narration ("HERON"), I must comply with the
terms and conditions of this HERON Data Use Agreement (the "Agreement").
I understand that the HERON data provided pursuant to this Agreement is
a limited data set as defined in section 45 CFR 164.514(e) of HIPAA's
Standards for Privacy of Individually Identifiable Health Information,
as amended from time to time, and shall be referred to herein as the
"Limited Data Set." I acknowledge that violation of this Agreement may
subject me to sanctions including but not limited to loss of request
privileges and/or institutional disciplinary action.
</h5>
<p></p>
<h4>1. DATA REQUEST SCOPE AND PURPOSE</h4>
<p></p>
<h5>A. Data Recipient agrees to use or disclose the Limited Data
Set only for the limited purposes necessary to conduct the following
research (enter Research Project Title and a brief description or attach
a supplemental research protocol):</h5>
<div>
<h5>&nbsp;&nbsp;Title of the Research:</h5>
</td>
<td><input type="text" name="txtRTitle" id="txtRTitle"
	value="<%=txtRTitleDisplay%>" size="120" maxlength="500">
</div>
<div>
<h5>&nbsp;&nbsp;Description of the Research:</h5>
</td>
<td><textarea rows="" cols="91" name="resDesc" id="resDesc"><%=resDescDisplay%></textarea>
</div><h5>
Data Recipient certifies that the research to be conducted is in an area
of Data Recipient's scientific expertise and that the data request is
limited in scope to the minimum information necessary to conduct the
research project described above (the "Research Project").
</h5><p></p>
<h5>B. The individuals, or classes of individuals, employed by KUMC
who shall be permitted by Data Recipient to use or receive the Limited
Data Set for purposes of the Research Project shall be limited to:
Network logon Ids of KUMC employees:</h5>
</td>
<td><textarea name="empIds" id="empIds" cols="91"><%=emplIdDisplay%></textarea>
<h5>(Separate by ;)</h5>
<p></p>
<h5>The individuals not employed by KUMC who shall be permitted by
Data Recipient to use or receive the Limited Data Set for purposes of
the Research Project shall be limited to:</h5>
<h5>Network logon Ids of <A HREF = "#affiliation">non-KUMC employees*</A>: </h5>
</td>
<td><textarea name="nonempIds" id="nonempIds" cols="91"><%=nonEmpIdDisplay%></textarea>
<h5>(Separate usernames by ; and put affilations in [].  <BR> For example: <b>rwaitman;dconnolly;</b> <BR><b>fsmith;lhargrove[Computer Science Professor at University of Kansas-Lawrence];afranks[Analyst at HCA Lee's Summit Medical Center]</B> )</h5>
<p></p>
<P ID=affiliation>
<h5>* For non-KUMC employees, include the position and employer for any students or staff who employed by another institution where there may need to be clarification regarding conflict of interest or competitive concerns between their parent institution and KUMC, KUH or UKP.</h5>
</P>

<h5>The individuals identified in sections 1.A and 1.B above shall
be referred to hereinafter as Data Recipient's "Research Team Members."
</h5>
<p></p>
<h3>
2. DATA RECIPIENT HEREBY AGREES:
</h3>
<p></p>
<h5>A. To fully comply with the requirements of the Health
Insurance Portability and Accountability Act of 1996 and regulations
promulgated thereunder, as may be amended from time to time ("HIPAA"),
including without limitation, 45 C.F.R. 164.514, throughout the term of
this Agreement. Data Recipient will not (and will cause any Research
Team Member not to) use or disclose the Limited Data Set in any manner
that would violate the requirements of HIPAA if Data Recipient or
Research Team Member were a Covered Entity.
<p></p>
B. Not to use or disclose the Limited Data Set or PHI except as
permitted under this Agreement. Without limiting the foregoing, Data
Recipient agrees to use the Limited Data Set or PHI only for bona fide
research purposes and to not use the Limited Data Set or PHI for
competitive institutional or individual advantage of any party other
than KUMC, the University of Kansas Hospital Authority, or Kansas
University Physicians, Inc. Data Recipient agrees to retain control over
the resulting Limited Data Set, to limit use and disclosure of the
Limited Data Set to the Research Team Members for the research purpose
described above, and to use appropriate administrative, physical and
technical safeguards, sufficient to comply with HIPAA, to prevent any
use or disclosure other than as provided for by this Agreement.
<p></p>
C. Data Recipient shall not allow use of his/her HERON user ID or
password by another individual. Data Recipient shall not disclose the
Limited Data Set to any person or entity except the Research Team
Members listed above on a need to know basis (and only then if such
Research Team Member has signed the Assurance of Compliance attached to
this Agreement), except with the prior written consent of the DROC.
<p></p>
D. Data Recipient agrees to require his/her Research Team Members to
agree to (i) the terms of this Data Use Agreement (evidenced by
execution of each Research Team Member of the Assurance of Compliance
attached to this Agreement) by executing and delivering to KUMC a copy
of this Data Use Agreement and (ii) the HERON business policies and
acknowledges his/her responsibility for ensuring appropriate use and
disclosure of the Limited Data Set by Data Recipient and the Research
Team Members.
<p></p>
E. Data Recipient shall not collaborate or allow collaboration with
industry regarding access to or use of the Limited Data Set, except with
the prior written consent of the Participant that supplied the data.
<p></p>
F. To report in writing to the KUMC Privacy Official at hipaa@kumc.edu
any use or disclosure of any portion of the Limited Data Set not covered
by this Agreement that becomes known, including without limitation, any
disclosure to an unauthorized subcontractor or any other individual or
entity not named in Section 1 above, within 48 hours of its discovery.
The Limited Data Set shall exclude the following direct identifiers of
the individual or of relatives, employers, or household members of the
individual: names, postal address information (other than town or city,
state, and zip code), telephone numbers, fax numbers, electronic mail
addresses, social security numbers, medical record numbers, health plan
beneficiary numbers, account numbers, certificate/license numbers,
vehicle identifiers and serial numbers (including license plate
numbers), device identifiers and serial numbers, web universal resource
locators (URLs), internet protocol (IP) address numbers, biometric
identifiers (including finger and voice prints), full face photographic
images, and any comparable images. See 45 C.F.R. 164.514(e)(2). In the
event that Data Recipient becomes aware of the inclusion in the Limited
Data Set of such an identifier set forth in 164.514(e)(2), Data
Recipient shall report such occurrence to HERON program staff (email:
phi_informatics@kumc.edu phone: 913-588-4703) and to the KUMC Privacy
Official (email: hipaa@kumc.edu).
<p></p>
G. Data User shall not, without the prior written consent of the DROC,
disclose the Limited Data Set on the basis that such disclosure is
required by law without notifying KUMC Office of General Counsel
(913-588-7281) and the KUMC Privacy Official (email: hipaa@kumc.edu), so
that KUMC shall have the opportunity to object to the disclosure and to
seek appropriate relief. To the extent that KUMC decides to assume
responsibility for challenging the validity of such request, Data
Recipient will cooperate fully with KUMC in any such challenge.
<p></p>
H. That the disposition of any intellectual property deriving from HERON
data acquisition and analysis requires the reporting of potential
"discoveries" to the KU Center for Technology Commercialization
(913-588-5439).
<p></p>
I. To acknowledge the HERON in all oral and written presentations,
disclosures, and publications resulting from any analyses of HERON
datasets. A sample statement to be used in acknowledgements is "The
dataset(s) used for the analyses described were obtained from the
University of Kansas Medical Center Healthcare Enterprise Repository for
Ontological Narration, which is supported by institutional funding and
is a joint effort between the Medical Center, the University of Kansas
Hospital, and Kansas University Physicians, Inc."
<p></p>
J. Not to identify the individuals contained in the Limited Data Set by
any means, including using participating organizations clinical systems
(Examples: O2, EPIC, IDX, Siemens) or other information (Example: Voter
Registration records) together with the Data Set, or to contact any
individual whose information is contained in the Limited Data Set.
<p></p>
K. To immediately destroy or return any data that Data User comes into
possession of that Data User is not authorized to possess pursuant to
the terms of this Data Use Agreement.
<p></p>
L. To not use the Limited Data Set or other information obtained from
HERON to make clinical or medical decisions.
<p></p>
M. To not, under any circumstance, sell the Limited Data Set, or any
data obtained from HERON.
<p></p>
</h5>
<h3>3. Term; Termination</h3>
<p></p>
<h5>A. Term. This Agreement shall be effective as of the date last
signed below and shall continue until (MM/DD/YYYY)
<input type="text" name="expDate" id="expDate" size="30" value="<%=expDateDisplay %>" maxlength="10"> 
or until the Agreement is terminated in accordance with the provisions for
termination below.
<p></p>
B. Termination. This Agreement may be unilaterally amended or terminated
at any time, by KUMC, the Data Request Oversight Committee, or either
the University of Kansas Hospital Authority or Kansas University
Physicians, Inc. in the event that Data Recipient breaches or violates a
material term of this Agreement.
<p></p>
C. Disposition of Records. Upon expiration or termination of this
Agreement, Data User will return or destroy any data accessed pursuant
to this Agreement. This section shall survive termination of this
Agreement.
<p></p>
</h5>
<h3>4. Miscellaneous Terms.</h3>
<p></p>
<h5>A. Publication. Data Recipient Agrees that research
publications arising from the use of the Limited Data Set shall contain
only aggregate data that does not specifically identify any individual
whose data or information is received pursuant to this Agreement unless
a specific authorization is obtained from the individual. With the
exception of the acknowledgement required in section 2.I, Data Recipient
further agrees not to publish any data derived from HERON (including
aggregate data on an institutional level basis) in a form that
identifies the institution that supplied the data, unless prior written
permission of the institution that supplied the data has been obtained.
Such data includes, without limitation, patient volume, patient charges
including any reimbursement data, either of the Participant's practice
patterns, and their respective quality and outcome measures.
<p></p>
B. KUMC Right of Access and Inspection. From time to time upon
reasonable notice, or upon reasonable determination by KUMC that Data
Recipient has breached this Agreement, KUMC may inspect the facilities,
systems, books and records of Data Recipient to monitor compliance with
this Agreement. System User understands and agrees that all proposed
query topics must be reviewed and approved by the HERON Data Request
Oversight Committee and that actual queries shall be audited for
adherence to such approval and the terms and conditions of this Data Use
Agreement.
<p></p>
C. Data Disclaimer. KUMC, the University of Kansas Hospital Authority
and Kansas University Physicians, Inc. disclaim all warranties as to the
accuracy of the data in HERON or the acceptable performance or fitness
of the data for any particular purpose. As such, the System User
acknowledges that KUMC, KUH and UKP do not and cannot warrant the
results that may be obtained by viewing data included in the Data Set,
and Data User accepts the Limited Data Set AS IS WITH ALL FAULTS.
<p></p>
D. Third Party Beneficiaries. The University of Kansas Hospital
Authority and Kansas University Physicians, Inc. are third-party
beneficiaries of this Agreement and shall be entitled to enforce any
obligation, responsibility or claim of KUMC pursuant to this Agreement.
</h5><p></p>
<h5>By typing my name below, I agree to the foregoing and confirm my electronic signature to this Agreement.</h5>
<p></p><h4>
AGREED TO AND ACCEPTED BY:</h4>
<p></p>
<h5>
Name: <%=uName%><p></p>
Title: <%=uTitle %><p></p>
</h5>
<h4>Principal Investigator Signature:<input type="text" maxlength="40" id="txtName" name="txtName" value="<%=sigValDisplay %>"/> 
Date(MM/DD/YYYY): <input type="text" name="txtSignDate" id="txtSignDate" maxlength="10" value="<%=sigDateDisplay %>" />  
</h4>
<p></p>
<div align="center"><input type="submit" name="agreementbtn"
	id="accept" value="Accept and Submit" /><input type="submit"
	id="cancel" name="agreementbtn" value="Cancel" /></div>
<p></p>
</form>
<%@ include file="footer.html"%>
</body>
</html>