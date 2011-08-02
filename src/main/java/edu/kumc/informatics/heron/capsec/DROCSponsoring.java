/*
 * To change this template, choose Tools | Templates
 * and open the template in the editor.
 */

package edu.kumc.informatics.heron.capsec;

import edu.kumc.informatics.heron.dao.HeronDBDao;
import org.springframework.mail.MailSender;
import org.springframework.mail.SimpleMailMessage;

/**
 *
 * @author dconnolly
 */
public class DROCSponsoring {
        private final HeronDBDao _heronData; // TODO: refactor
        private final MailSender _mailSender;
        private final SimpleMailMessage _templateMessage;
        private final Enterprise _enterprise;

        public DROCSponsoring(Enterprise e, HeronDBDao hd, MailSender ms, SimpleMailMessage sm) {
                _enterprise = e;
                _heronData = hd;
                _mailSender = ms;
                _templateMessage = sm;
        }


        public void postRequest(String title, Sponsor a1, Agent a2) {
                SimpleMailMessage msg = new SimpleMailMessage(_templateMessage);
                msg.setTo(mailboxes());
                _mailSender.send(msg);
        }

        public String mailboxes() {
                StringBuilder accum = new StringBuilder();

                for (String n: _heronData.getDrocIds()) {
                        accum.append(_enterprise.affiliate(n).getMail());
                        accum.append(", ");
                }

                return accum.toString();
        }
}
