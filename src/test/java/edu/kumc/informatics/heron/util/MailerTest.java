package edu.kumc.informatics.heron.util;

import java.util.Collections;

import javax.mail.MessagingException;
import javax.mail.Message;
import javax.mail.Header;

import org.junit.Test;
import static org.junit.Assert.assertEquals;

public class MailerTest {
        @Test
        public void itShouldRenderATrivialMessage() throws MessagingException{
                Mailer mailer = new Mailer("smtp.example");
                Message msg = mailer.render("", "sender@example",
                        "recip@example", "", "");
                String[] hf = {"From"};
                assertEquals("sender@example",
                        ((Header)msg.getMatchingHeaders(hf).nextElement()).getValue() );
        }

        @Test
        public void itShouldSendATrivialMessage() throws MessagingException {
                Mailer mailer = new Mailer("smtp.example");
                Message msg = mailer.render("", "sender@example",
                        "recip@example", "", "");
                mailer.send(msg);
        }
}
