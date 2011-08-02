/* Copyright (c) 2011 The University of Kansas Medical Center
 * http://informatics.kumc.edu/ */

package edu.kumc.informatics.heron.capsec;

import java.util.List;
import javax.naming.NamingException;
import javax.naming.directory.Attributes;
import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;
import org.springframework.ldap.core.AttributesMapper;
import org.springframework.ldap.core.LdapTemplate;

/**
 * An EnterpriseAuthority derives capabilities from a CASCheck using LDAP.
 * @author dconnolly
 */
public class Enterprise {
        protected final Log logger = LogFactory.getLog(getClass());

        private LdapTemplate _ldapTemplate;

        /**
         *
         * @param t as per SpringLDAP
         * http://static.springsource.org/spring-ldap/docs/1.3.x/reference/html/basic.html
         */
        public Enterprise (LdapTemplate t) {
                _ldapTemplate = t;
        }

        private static final SecurityException denied = new SecurityException(
                                "Declined by Enterprise Directory (LDAP)");

        private AccountHolder findByName(String name) throws SecurityException {
                List x = _ldapTemplate.search("", "(cn=" + name + ")",
                        new AttributesMapper() {
                                @Override
                                public Object mapFromAttributes(Attributes attrs)
                                        throws NamingException {
                                        return new AccountHolder(
                                                (String)attrs.get("sn").get(),
                                                (String)attrs.get("givenname").get(),
                                                (String)attrs.get("mail").get(),
                                                "Y".equals((String)attrs.get("kumcPersonFaculty").get()),
                                                (String)attrs.get("kumcPersonJobcode").get());
                                        // any use for "title"?
                                }
                        });
                if (x.isEmpty()) {
                        throw denied;
                }
                /* TODO: else if x.size() > 1 ... */
                return (AccountHolder)x.get(0); // ugh... cast...
        }

        public Agent recognize(Agent who) throws IllegalArgumentException {
                try {
                        return (AccountHolder)who;
                } catch (ClassCastException e) {
                        throw denied;
                }
        }

        public static final String excluded_jobcode = "24600";
        static class AccountHolder implements Agent {
                public AccountHolder(String surName, String givenName, String mail,
                        Boolean isFaculty, String jobCode) {
                        _surName = surName;
                        _givenName = givenName;
                        _mail = mail;
                        _isFaculty = isFaculty;
                        _jobCode = jobCode;
                }

                private final String _surName;
                private final String _givenName;
                private final String _mail;
                private final Boolean _isFaculty;
                private final String _jobCode;

                public Boolean isQualifiedFaculty() {
                        return _isFaculty && ! _jobCode.equals(excluded_jobcode);
                }

                @Override
                public String getFullName(){
                        return _givenName + " " + _surName;
                }

                @Override
                public String getMail(){
                        return _mail;
                }
        }

        public Agent affiliate(String name) {
                return findByName(name);
        }

        public Agent qualifiedFaculty(Ticket who) {
                AccountHolder a = findByName(who.getName());

                if (!a.isQualifiedFaculty()) {
                        throw denied;
                }
                return a;
        }
}
