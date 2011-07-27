/* Copyright (c) 2011 The University of Kansas Medical Center
 * http://informatics.kumc.edu/ */

package edu.kumc.informatics.heron.util;

import edu.kumc.informatics.heron.dao.PostSponsorshipRequest;
import java.util.List;
import javax.naming.NamingException;
import javax.naming.directory.Attributes;
import javax.servlet.ServletException;
import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;
import org.springframework.ldap.core.AttributesMapper;
import org.springframework.ldap.core.LdapTemplate;

/**
 * An EnterpriseAuthority derives capabilities from a CASCheck using LDAP.
 * @author dconnolly
 */
public class EnterpriseAuthority {
        protected final Log logger = LogFactory.getLog(getClass());

        private LdapTemplate _ldapTemplate;

        /**
         * Derive a CASCap from a CAS-filtered HttpServletRequest.
         * @param t as per SpringLDAP
         * http://static.springsource.org/spring-ldap/docs/1.3.x/reference/html/basic.html
         */
        public EnterpriseAuthority (LdapTemplate t) {
                _ldapTemplate = t;
        }

        private static final Exception noCAS = new Exception(
                                "Declined by Enterprise Directory (LDAP)");

        private Employee findByName(String name) throws NamingException{
                List x = _ldapTemplate.search("", "(cn=" + name + ")",
                        new AttributesMapper() {
                                @Override
                                public Object mapFromAttributes(Attributes attrs)
                                        throws NamingException {
                                        return new Employee(
                                                (String)attrs.get("sn").get(),
                                                (String)attrs.get("givenname").get(),
                                                (String)attrs.get("mail").get(),
                                                "Y".equals((String)attrs.get("kumcPersonFaculty").get()),
                                                (String)attrs.get("kumcPersonJobcode").get());
                                        // any use for "title"?
                                }
                        });
                if (x.isEmpty()) {
                        throw new NamingException("not found");
                }
                /* TODO: else if x.size() > 1 ... */
                return (Employee)x.get(0); // ugh... cast...
        }

        public static final String excluded_jobcode = "24600";
        static class Employee {
                public Employee(String surName, String givenName, String mail,
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

                public String getFullName(){
                        return _givenName + " " + _surName;
                }

                public String getMail(){
                        return _mail;
                }
        }

        public String getFullName(CASCheck who) throws NamingException, ServletException{
                return findByName(who.getName()).getFullName();
        }

        public String getMail(CASCheck who) throws NamingException, ServletException{
                return findByName(who.getName()).getMail();
        }

        public PostSponsorshipRequest sponsorship(CASCheck cap) throws NamingException, ServletException {
                if (findByName(cap.getName()).isQualifiedFaculty()) {
                        return new PostSponsorshipRequest();
                } else {
                        /* TODO: re-work error message to balance security with usability */
                        throw new ServletException("insufficient privilege");
                }
        }

}
