package edu.kumc.informatics.heron.servlet;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Date;
import java.util.List;
import java.io.IOException;
import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import javax.servlet.RequestDispatcher;
import javax.servlet.ServletException;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import javax.servlet.http.HttpSession;

import org.apache.commons.logging.LogFactory;
import org.apache.commons.logging.Log;
import org.springframework.mail.MailSender;
import org.springframework.mail.SimpleMailMessage;

import edu.kumc.informatics.heron.util.DBUtil;
import edu.kumc.informatics.heron.util.Functional;
import edu.kumc.informatics.heron.util.LdapUtil;
import edu.kumc.informatics.heron.util.Functional.Pair;
import edu.kumc.informatics.heron.util.Functional.Predicate;
import static edu.kumc.informatics.heron.base.StaticValues.*;

/**
 * Servlet implementation class SponsorshipServlet to handle user sponsorship.
 * 
 * D. zhu
 */
public class SponsorshipServlet extends HttpServlet {
	private static final long serialVersionUID = 1L;
	private LdapUtil ldapUtil = new LdapUtil();
        private DBUtil dbUtil;
        private final Log logger = LogFactory.getLog(this.getClass());

        @Override
        public void init() {
                dbUtil = (DBUtil) SpringServletHelper.getBean(getServletContext(),
                        DBUtil.Beans.USER_ACCESS_DATA);
                assert dbUtil != null;
        }


        /**
	 * @see HttpServlet#doGet(HttpServletRequest request, HttpServletResponse response)
	 */
        @Override
	protected void doGet(HttpServletRequest request, HttpServletResponse response) throws ServletException, IOException {
		String initType = request.getParameter("init_type");

                if (initType != null) {
                        String uid = request.getRemoteUser();
                        String[] info = ldapUtil.getUserInfo(uid);
                        HttpSession session = request.getSession();
                        session.setAttribute(USER_FULL_NAME, info[0]);
                        session.setAttribute(USER_TITLE, info[2]);
                        boolean isQualified = dbUtil.checkQualification(info[1], info[3], uid);

                        if (!isQualified) {
                                String message = "sorry, only qualified falcuties who have signed HERON system access agreement can use this functionality."
                                        + "<p><p> Please use link <a href=\"AuthServlet?SPNSR=Y&init_type="
                                        + initType + "\">Sign System Access Agreement</a> if you a qualified faculty.";
                                request.setAttribute(VAL_MESSAGE, message);
                                RequestDispatcher rd = request.getRequestDispatcher(GEN_DISPLAY_URL);
                                rd.forward(request, response);
                        } else {
                                String url = initType.equals(VIEW_ONLY) ? SPONSOR_URL : DATA_USAGE_URL;
                                RequestDispatcher rd = request.getRequestDispatcher(url);
                                rd.forward(request, response);
                        }
                } else {
                        response.sendRedirect(DENIED_URL);
                }
	}

	/**
	 * @see HttpServlet#doPost(HttpServletRequest request, HttpServletResponse response)
	 */
        @Override
	protected void doPost(HttpServletRequest request, HttpServletResponse response) throws ServletException, IOException {
		String type = request.getParameter("agreementbtn");
		String initType = request.getParameter("init_type");
		
		if("Accept and Submit".equals(type)){//submit sponsorship
			String spnsrType = request.getParameter("spnsr_type");
			String backUrl = spnsrType.equals(VIEW_ONLY)?SPONSOR_URL:DATA_USAGE_URL;
                        Input in = new Input(request);

                        StringBuilder msgs = new StringBuilder(in.messages());
                        ldapValidate(in.employeeIds, ldapUtil, msgs,
                                "The following employee ids are not in LDAP: ");
                        ldapValidate(in.nonEmployees.getLeft(), ldapUtil, msgs,
                                "The following non-KUMC employee id not in LDAP: ");

                        /* TODO: figure out a sane alternative to passing info this way. */
                        HttpSession session = request.getSession();
                        session.setAttribute(Form.NON_EMP_IDS, in.nonEmployees.getLeft().toArray());
                        session.setAttribute(Form.NON_EMP_DESCS, in.nonEmployees.getRight().toArray());

                        if (in.employeeIds.size() + in.nonEmployees.getLeft().size() > 0) {
                                List<String> ids = Functional.append(in.employeeIds, in.nonEmployees.getLeft());
                                String sponsoredMsg = dbUtil.isSponsoredCheck(ids, in.resTitle, in.resDesc, in.spnsrType);
                                if (!"".equals(sponsoredMsg)) {
                                        msgs.append("The following ID(s) has already been sponsored for the same research title and description: ");
                                        msgs.append(sponsoredMsg);
                                        msgs.append(". ");
                                }
                        }


                        String message = msgs.toString();
			if("".equals(message)){
				String result = spnsrType.equals(VIEW_ONLY)?"User(s) Sponsored Successfully !":"Data Usage Agreement Submitted Successfully!";
				try{
					dbUtil.insertSponsorships(request);
					sendNotificationEmailToDroc();
				}catch(Exception ex){
					result = "Sorry, unexpected error with database update: " + ex.getMessage();
				}
				request.setAttribute(VAL_MESSAGE, result);
				RequestDispatcher rd = request.getRequestDispatcher(GEN_DISPLAY_URL);
				rd.forward(request, response);
			}
			else{
				request.setAttribute(VAL_MESSAGE, message);
				RequestDispatcher rd = request.getRequestDispatcher(backUrl);
				rd.forward(request, response);
			}
		}
		else{//deny/cancel sponsorship
			response.sendRedirect(DENIED_URL);
		}
	}


        public static final SimpleDateFormat mmddyyyy = new SimpleDateFormat(
                "MM/dd/yyyy");


        /**
         * These names are part of the public interface because
         * they must match the names used in the HTML markup,
         * not to mention testing.
         */
        public static interface Form {
                String TITLE = "txtRTitle";
                String DESC = "resDesc";
                String EMPIDS = "empIds";
                String NONEMPIDS = "nonempIds";
                String SPONSOR_TYPE = "spnsr_type";
                String EXPIRATION_DATE = "expDate";
                String SIGNER_NAME = "txtName";
                String SIGN_DATE = "txtSignDate";

                // TODO: get rid of these goofy things.
                String NON_EMP_IDS = "NON_EMP_IDS";
                String NON_EMP_DESCS = "NON_EMP_DESCS";
        }

        public static class Input {
                private final StringBuilder msgs = new StringBuilder();
                final String resTitle;
                final String resDesc;
                final List<String> employeeIds; // TODO: private?
                final Pair<ArrayList<String>, ArrayList<String>> nonEmployees;
                final String spnsrType;
                private final String expDate;
                private String sigName; // TODO: make this final
                private String sigDate;

                public Input(HttpServletRequest request) {
                        resTitle = requiredField(request, Form.TITLE, msgs,
                                "Title of Research is required. ");
                        resDesc = requiredField(request, Form.DESC, msgs,
                                "Description of the Research is required. ");

                        employeeIds = Arrays.asList(trimField(request, Form.EMPIDS).split("\\s*;\\s*"));
                        Pair<ArrayList<String>, ArrayList<String>> nonempl;
                        try {
                                nonempl = parseNonEmployees(trimField(request, Form.NONEMPIDS));
                        } catch (IllegalArgumentException e) {
                                msgs.append("The non-KUMC employee data format is incorrect.");
                                msgs.append(e.getMessage());
                                nonempl = new Pair<ArrayList<String>, ArrayList<String>>(
                                        new ArrayList<String>(), new ArrayList<String>());
                        }
                        nonEmployees = nonempl;

                        if (employeeIds.size() + nonEmployees.getLeft().size() < 1)
                                msgs.append("Must enter employee Id(s) or non-KUMC employee Id(s). ");

                        spnsrType = request.getParameter(Form.SPONSOR_TYPE);

                        expDate = trimField(request, Form.EXPIRATION_DATE);
                        if (!"".equals(expDate)) {
                        try {
                                Date d = mmddyyyy.parse(expDate);
                        } catch (ParseException e) {
                                msgs.append("Expiration Date format invalid. ");
                                }
                        }

                        if (spnsrType.equals(DATA_ACCESS)) {
                                sigName = requiredField(request, Form.SIGNER_NAME, msgs,
                                        "Signature is required. ");
                                sigDate = requiredField(request, Form.SIGN_DATE, msgs,
                                        "Signature Date is required. ");
                                try {
                                        Date d = mmddyyyy.parse(sigDate);
                                } catch (ParseException e) {
                                        msgs.append("Signature Date format is wrong.");
                                }
                        }
                }

                public String messages() {
                        return msgs.toString();
                }

                protected static String trimField(HttpServletRequest request, String name) {
                        String value = request.getParameter(name);
                        if (value == null) {
                                return "";
                        } else {
                                return value.trim();
                        }
                }

                protected static String requiredField(HttpServletRequest request, String name,
                        StringBuilder errs, String faultMessage) {
                        String value = request.getParameter(name);
                        if (value == null || "".equals(value.trim())) {
                                errs.append(faultMessage);
                        }
                        return value;
                }

                /**
                 * Parse (name [description]?)+ string.
                 *
                 * This is a hokey UI; we should use separate form fields.
                 * @param text
                 * @return a list of names and descriptions
                 * @throws IllegalArgumentException if the format is bad
                 */
                protected static Pair<ArrayList<String>, ArrayList<String>> parseNonEmployees(String text) {
                        assert text != null;

                        // strange: "".split(";") gives Array("")
                        if("".equals(text)){
                                return new Pair<ArrayList<String>, ArrayList<String>>(
                                        new ArrayList<String>(),
                                        new ArrayList<String>());
                        }
                        String[] parts = text.split("\\s*;\\s*");

                        ArrayList<String> names = new ArrayList<String>(parts.length);
                        ArrayList<String> descriptions = new ArrayList<String>(parts.length);

                        for (String part : parts) {
                                Matcher m = personDesc.matcher(part);

                                if (m.matches()) {
                                        names.add(m.group(1));
                                        descriptions.add(m.group(2));
                                } else {
                                        throw new IllegalArgumentException(
                                                "expected name [description]; found: " + part);
                                }
                        }

                        return new Pair<ArrayList<String>, ArrayList<String>>(names, descriptions);
                }
                static final Pattern personDesc = Pattern.compile(
                "\\s*([^;\\[\\]\\s]+)\\s*(?:\\[([^\\[\\];]+)\\])?\\s*;?");
        }

        protected void ldapValidate(List<String> candidates, final LdapUtil ldapUtil,
                StringBuilder msgs, String failureMessage) {

                logger.info("@@checking users: " + candidates);

                List<String> unknowns = Functional.filter(candidates,
                        new Predicate<String>() {
                                @Override
                                public Boolean apply(String id) {
                                        logger.info("@@checking user: " + id);
                                        return !ldapUtil.isUserInLdap(id);
                                }
                        });
		if(!unknowns.isEmpty()) {
			msgs.append(failureMessage);
                        msgs.append(Functional.mkString(unknowns, " "));
                        msgs.append(". ");
                }
        }


        // cf http://static.springsource.org/spring/docs/2.0.6/reference/mail.html
        private MailSender mailSender;
        public void setMailSender(MailSender v) {
                mailSender = v;
        }

        private SimpleMailMessage templateMessage;
        public void setTemplateMessage(SimpleMailMessage templateMessage) {
                this.templateMessage = templateMessage;
        }

	/**
	 * send email to droc team for heron approval
	 * @param toEmails
	 */
	private void sendNotificationEmailToDroc(){
                // Create a thread safe "copy" of the template message and customize it
                SimpleMailMessage msg = new SimpleMailMessage(this.templateMessage);
                msg.setTo(ldapUtil.getDrocEmails(dbUtil.getDrocIds()));

                this.mailSender.send(msg);
        }
}
