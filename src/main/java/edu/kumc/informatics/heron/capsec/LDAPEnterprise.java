/* Copyright (c) 2011 The University of Kansas Medical Center
 * http://informatics.kumc.edu/ */

package edu.kumc.informatics.heron.capsec;

import java.security.acl.NotOwnerException;
import java.util.List;
import javax.naming.NameNotFoundException;
import javax.naming.NamingException;
import javax.naming.NoPermissionException;
import javax.naming.directory.Attributes;
import javax.servlet.http.HttpServletRequest;
import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;
import org.jasig.cas.client.util.AbstractCasFilter;
import org.jasig.cas.client.validation.Assertion;
import org.springframework.ldap.core.AttributesMapper;
import org.springframework.ldap.core.LdapTemplate;

/**
 * An EnterpriseAuthority derives capabilities from a CASCheck using LDAP.
 * @author dconnolly
 */
public class LDAPEnterprise implements AcademicMedicalCenter {
        protected final Log logger = LogFactory.getLog(getClass());

        private final LdapTemplate _ldapTemplate;

        /**
         *
         * @param t as per SpringLDAP
         * http://static.springsource.org/spring-ldap/docs/1.3.x/reference/html/basic.html
         */
        public LDAPEnterprise (LdapTemplate t) {
                _ldapTemplate = t;
        }

        private static final NameNotFoundException notfound = new NameNotFoundException (
                                "Not in Enterprise Directory (LDAP)");

        /**
         * TODO: fix ldap injection
         * @param name
         * @return
         * @throws NameNotFoundException 
         */
        private AccountHolder findByName(String name) throws NameNotFoundException {
                final LDAPEnterprise that = this;
                List x = _ldapTemplate.search("", "(cn=" + name + ")", //TODO: FIXME
                        new AttributesMapper() {
                                @Override
                                public Object mapFromAttributes(Attributes attrs)
                                        throws NamingException {
                                        return new AccountHolder(that,
                                                (String)attrs.get("sn").get(),
                                                (String)attrs.get("givenname").get(),
                                                (String)attrs.get("mail").get(),
                                                "Y".equals((String)attrs.get("kumcPersonFaculty").get()),
                                                (String)attrs.get("kumcPersonJobcode").get());
                                        // any use for "title"?
                                }
                        });
                if (x.isEmpty()) {
                        throw notfound;
                }
                /* TODO: else if x.size() > 1 ... */
                return (AccountHolder)x.get(0); // ugh... cast...
        }

        private NotOwnerException notmine = new NotOwnerException();
        /**
         * Ensure that an agent is an agent of this organization.
         * @param who
         * @return who, verified to be an agent of this organization
         * @throws NotOwnerException if who is not recognized
         */
        @Override
        public Agent recognize(Agent who) throws NotOwnerException {
                AccountHolder out;
                try {
                        out = (AccountHolder)who;
                } catch (ClassCastException e) {
                        throw notmine;
                }
                if (out._org != this) {
                        throw notmine;
                }
                return out;
        }

        public static final String excluded_jobcode = "24600";
        static class AccountHolder implements Agent {
                public AccountHolder(LDAPEnterprise org,
                        String surName, String givenName, String mail,
                        Boolean isFaculty, String jobCode) {
                        _org = org;
                        _surName = surName;
                        _givenName = givenName;
                        _mail = mail;
                        _isFaculty = isFaculty;
                        _jobCode = jobCode;
                }

                private final LDAPEnterprise _org;
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

        @Override
        public Agent affiliate(String name) throws NameNotFoundException {
                return findByName(name);
        }

        /**
         * Hmm... perhaps we should be involved in the generation of tickets.
         * Else why not just use a String?
         * @param who
         * @return
         * @throws LimitExceededException
         */
        @Override
        public Agent qualifiedFaculty(Ticket who) throws NoPermissionException {
                CASTicket cas_who;
                
                try {
                        cas_who = (CASTicket)who;
                } catch (ClassCastException e) {
                        throw denied;
                }
                if (cas_who._enterprise != this) {
                        throw denied;
                }

                AccountHolder a;
                try {
                        a = findByName(cas_who.getName());
                } catch (NameNotFoundException e) {
                        throw denied;
                }

                if (!a.isQualifiedFaculty()) {
                        throw denied;
                }
                return a;
        }
        private NoPermissionException denied = new NoPermissionException();

        
        /**
         * Derive a CASCap from a CAS-filtered HttpServletRequest.
         * @param request
         * @return a CASCap that gives access to the name of the authenticated CAS Principal.
         * @throws ServletException if the request's session has no CAS assertion attribute.
         */
        public Ticket asTicket(HttpServletRequest request)  throws SecurityException {
                // Rescue Assertion from un-typesafe attribute mapping.
                Assertion it = (Assertion)request.getSession().getAttribute(
                        AbstractCasFilter.CONST_CAS_ASSERTION);
                if (it == null){
                        throw noCAS;
                }

                return new CASTicket(this, it.getPrincipal().getName());
        }
        
        protected static final SecurityException noCAS =
                new SecurityException("no CAS ticket");

        /**
         * A CASTicket is a capability derived from a CAS-authenticated HttpServletRequest.
         * @author dconnolly
         */
        private static class CASTicket implements Ticket {
                private final String _name;
                private final LDAPEnterprise _enterprise;
                
                protected CASTicket (LDAPEnterprise e, String name) {
                        _enterprise = e;
                        _name = name;
                }

                @Override
                public String getName() {
                        return _name;
                }

        }
}
