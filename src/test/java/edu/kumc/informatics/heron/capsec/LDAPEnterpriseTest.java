/* Copyright (c) 2011 The University of Kansas Medical Center
 * http://informatics.kumc.edu/ */

package edu.kumc.informatics.heron.capsec;

import java.util.HashMap;
import java.util.Map;
import javax.naming.NameNotFoundException;
import javax.naming.directory.Attributes;
import javax.naming.directory.BasicAttributes;
import javax.naming.directory.DirContext;
import javax.xml.xpath.XPathExpressionException;
import org.w3c.dom.Node;
import org.xml.sax.InputSource;

import org.junit.Test;
import org.junit.Assert;

import org.springframework.ldap.NamingException;
import org.springframework.ldap.core.ContextSource;
import org.springframework.ldap.core.LdapTemplate;

import edu.kumc.informatics.heron.util.HCardContext;

public class LDAPEnterpriseTest {
        public static final String mockData = "/mockDirectory.html";

        @Test
        public void findKnownAgent() throws NameNotFoundException {
            LdapTemplate cardsTemplate = new LdapTemplate(new HCardSource());
            LDAPEnterprise e = new LDAPEnterprise(cardsTemplate);
            Assert.assertEquals("John Smith", e.affiliate("john.smith").getFullName());
        }

        @Test(expected= NameNotFoundException.class)
        public void dontFindUnknownAgent() throws NameNotFoundException {
            LdapTemplate cardsTemplate = new LdapTemplate(new HCardSource());
            LDAPEnterprise e = new LDAPEnterprise(cardsTemplate);
            Agent _ = e.affiliate("nobody.we.know");
        }


        public static class KUMCHCardContext extends HCardContext {
            public KUMCHCardContext(InputSource hCardSrc){
                super(hCardSrc);
            }

            private static final Map<String, String> ldap2hcard = new HashMap<String, String>() {
                {
                    put("sn", "family-name");
                    put("givenname", "given-name");
                    put("mail", "email");
                    put("kumcPersonFaculty", "kumcPersonFaculty");
                    put("kumcPersonJobcode", "kumcPersonJobcode");
                }
            };
            public Attributes cardAttributes(Node hcard) {
                BasicAttributes out = new BasicAttributes();
                for (String ldapattr : ldap2hcard.keySet()) {
                    String hcardClass = ldap2hcard.get(ldapattr);
                    String findByClass = ".//*[@class='" + hcardClass + "']/text()";
                    String value;
                    try {
                        value = xpath.evaluate(findByClass, hcard);
                    } catch (XPathExpressionException ex) {
                        throw new RuntimeException("Bad XPath defined at design time:" + findByClass, ex);
                    }
                    out.put(ldapattr, value);    
                }
                return out;
            }
        }

        /**
         * Spring ContextSource to build a KUMCHCardContext
         */
        public static class HCardSource implements ContextSource {
            
            @Override
            public DirContext getReadOnlyContext() throws NamingException {
                InputSource src =
                        new InputSource(getClass().getResourceAsStream(mockData));
                return new KUMCHCardContext(src);
            }
            
            @Override
            public DirContext getReadWriteContext() throws NamingException {
                throw new UnsupportedOperationException("Not supported yet.");
            }
            
            /**
             * I'm not sure this is faithful to the interface...
             * @param u
             * @param p
             * @return
             * @throws NamingException 
             */
            @Override
            public DirContext getContext(String u, String p) throws NamingException {
                return getReadOnlyContext();
            }
        }        
}

