/* Copyright (c) 2011 The University of Kansas Medical Center
 * http://informatics.kumc.edu/ */

package edu.kumc.informatics.heron.capsec;

import static edu.kumc.informatics.heron.base.StaticValues.RAVEN_URL;

import java.util.ArrayList;
import java.util.Collections;
import java.util.Enumeration;
import java.util.List;
import java.util.Properties;
import java.util.Vector;

import edu.kumc.informatics.heron.dao.HeronDBDao;
import edu.kumc.informatics.heron.dao.HeronDao;
import edu.kumc.informatics.heron.dao.HeronDao.ApprovalStatus;
import edu.kumc.informatics.heron.dao.HeronDao.ParticipatingOrg;
import edu.kumc.informatics.heron.util.StaticDataUtil;
import edu.kumc.informatics.heron.util.Functional.Pair;

import javax.mail.Address;
import javax.mail.Message;
import javax.mail.Session;
import javax.mail.Transport;
import javax.mail.internet.InternetAddress;
import javax.mail.internet.MimeMessage;
import javax.naming.NameNotFoundException;
import javax.servlet.ServletException;
import javax.servlet.http.HttpServletRequest;

import org.springframework.mail.MailSender;
import org.springframework.mail.SimpleMailMessage;

/**
 *
 * @author dconnolly
 */
public class DROCSponsoring {
        private final HeronDBDao _heronData;
        private final MailSender _mailSender;
        private final SimpleMailMessage _templateMessage;
        private final AcademicMedicalCenter _enterprise;

        public DROCSponsoring(AcademicMedicalCenter e, HeronDBDao hd, MailSender ms, SimpleMailMessage sm) {
                _enterprise = e;
                _heronData = hd;
                _mailSender = ms;
                _templateMessage = sm;
        }

        /**
         * approve sponsorships.
         * @param request
         * @return false if there were no decisions in the request.
         * @throws ServletException 
         * @throws NameNotFoundException 
         */
        public boolean approveSponsorship(HttpServletRequest request) throws ServletException, NameNotFoundException{
                final ArrayList<Pair<Integer, ApprovalStatus>> decisions = new ArrayList<Pair<Integer, ApprovalStatus>>();
                @SuppressWarnings("unchecked")
                final Enumeration<String> names = request.getParameterNames();
                final ParticipatingOrg org;
                try {
                	org = ParticipatingOrg.valueOf(request.getParameter("hidOrg"));
                } catch (IllegalArgumentException badArg) {
                	return false;
                }
                
                while(names.hasMoreElements()){
                        String param = names.nextElement()+"";
                        if(param.startsWith("rad_")){
                                Integer id = Integer.parseInt(param.substring(4));
                                String val = request.getParameter(param);
                                if(val!=null){
                                        decisions.add(new Pair<Integer, ApprovalStatus>(id,
                                        		val == "A" ? ApprovalStatus.A : ApprovalStatus.D));
                                }
                        }
                }

                if(!decisions.isEmpty()){
                        final Agent reviewer = _enterprise.affiliate(request);
                        final HeronDao.DrocAccess d = _heronData.drocAccess(reviewer);
                        d.approveSponsorship(org, decisions);
                        notifyUserApprovedOrRejected(decisions);
                }
                
                return !decisions.isEmpty();
        }
        

        /**
         * notify user and sponsor if request/sponsorship get rejected or approved
         * @param ids
         * @param vals
         * @throws NameNotFoundException 
         */
        private void notifyUserApprovedOrRejected(List<Pair<Integer, ApprovalStatus>> decisions) throws NameNotFoundException{
                for(Pair<Integer, ApprovalStatus>d: decisions){                
                	ApprovalStatus s = d.getRight();
                	Integer spnId = d.getLeft();
                        if(s == ApprovalStatus.A){
                                String[] approveInfo = _heronData.getUserApproveInfo(spnId.intValue());
                                if(approveInfo[0]=="T"){
                                        notifyUserApprovedOrRejected(_enterprise.affiliate(approveInfo[1]),
                                        		_enterprise.affiliate(approveInfo[2]), s, approveInfo[3]);
                                }
                                //TODO: test for else...?
                        }
                        else if (s == ApprovalStatus.D){
                                String[] spsrInfo = _heronData.getSponsorshipUserInfo(spnId.intValue());
                                notifyUserApprovedOrRejected(_enterprise.affiliate(spsrInfo[0]),
                                		_enterprise.affiliate(spsrInfo[1]), s,
                                		spsrInfo[2]);
                        }
                }
        }
        

	/**
	 * send notification emails to User about sponsorship Approval Or
	 * Rejection
	 * 
	 * @param userId
	 * @param sponsorId
	 * @param type
	 */
	public void notifyUserApprovedOrRejected(Agent user, Agent sponsor,
	                ApprovalStatus type, String proj) {
		String subj = "HERON access request ";
		// TODO: use StringTemplate
		String contn = "Dear "
		                + sponsor.getFullName()
		                + ",\n \n "
		                + "The HERON Data Request Oversight Committee has ";
		Properties props = StaticDataUtil.getSoleInstance()
		                .getProperties();

		if (type == ApprovalStatus.A) {
			subj += "approved!";
			contn += "approved access for "
			                + user.getFullName()
			                + " for project ("
			                + proj
			                + "). "
			                + "He/she will be required to sign a system access agreement if it has not been done so "
			                + "already for another project. He/she can login to  "
			                + props.getProperty(RAVEN_URL)
			                + " and then access the HERON link on the left. If you have any questions, feel free to email heron-admin@kumc.edu.\n\n";
		} else {
			subj += "denied!";
			contn += "denied access for "
			                + user.getFullName()
			                + " for project ("
			                + proj
			                + ").\n\n"
			                + "If you have any questions or want to voice concerns, please email heron-admin@kumc.edu and"
			                + " we will escalate your concerns to KUMC, UKP and KUH leadership. \n \n";
		}
		contn += "Sincerely, \n \n" + "The HERON Team.";

		SimpleMailMessage msg = new SimpleMailMessage(_templateMessage);
		msg.setSubject(subj);
		msg.setTo(sponsor.getMail());
		msg.setCc(user.getMail());
		msg.setText(contn);
		_mailSender.send(msg);
	}


	// oops... this class has become schizophrenic.
	// it was for making requests, but now it's for reviewing them.
        private String mailboxes() throws NameNotFoundException {
                StringBuilder accum = new StringBuilder();

                for (String n: _heronData.getDrocIds()) {
                        accum.append(_enterprise.affiliate(n).getMail());
                        accum.append(", ");
                }

                return accum.toString();
        }
}
