package edu.kumc.informatics.heron.util;

import java.util.Properties;
import javax.mail.Address;
import javax.mail.Message;
import javax.mail.MessagingException;
import javax.mail.Session;
import javax.mail.internet.InternetAddress;
import javax.mail.internet.MimeMessage;
import javax.mail.Transport;

/**
 * Mailer provides mail service for a servlet session.
 */
public class Mailer {
        private Session _session;

        public Mailer(String host) {
                Properties mailProps = new Properties();
                mailProps.put("mail.smtp.host", host);
                _session = Session.getInstance(mailProps, null);
        }

        /**
         * Build Message from subject, from/to/cc, and body.
         */
        public Message render(String subject,
                String fromAddr,
                String to_field, String cc_field,
                String body) throws MessagingException {
                MimeMessage msg = new MimeMessage(_session);
                Address[] addrs = InternetAddress.parse(to_field);
                Address[] ccAddrs = InternetAddress.parse(cc_field);
                msg.setText(body);
                msg.setFrom(new InternetAddress(fromAddr));
                msg.setRecipients(Message.RecipientType.TO, addrs);
                msg.setRecipients(Message.RecipientType.CC, ccAddrs);
                msg.setSubject(subject);
                return msg;
        }

        public void send(Message msg) throws MessagingException {
                Transport.send(msg);
        }
}
