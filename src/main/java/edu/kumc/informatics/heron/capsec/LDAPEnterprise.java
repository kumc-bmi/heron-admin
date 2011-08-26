/* Copyright (c) 2011 The University of Kansas Medical Center
 * http://informatics.kumc.edu/ */

package edu.kumc.informatics.heron.capsec;

import java.util.Date;
import java.util.List;
import javax.naming.NameNotFoundException;
import javax.naming.NamingException;
import javax.naming.NoPermissionException;
import javax.naming.directory.Attributes;
import javax.servlet.ServletException;
import javax.servlet.http.HttpServletRequest;
import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;
import org.jasig.cas.client.util.AbstractCasFilter;
import org.jasig.cas.client.validation.Assertion;
import org.springframework.ldap.core.AttributesMapper;
import org.springframework.ldap.core.LdapTemplate;

import edu.kumc.informatics.heron.dao.ChalkDao;
import edu.kumc.informatics.heron.util.Functional.Function1;

/**
 * @author dconnolly
 */
//TODO: rename this class.
public class LDAPEnterprise implements AcademicMedicalCenter {

        protected final Log logger = LogFactory.getLog(getClass());

        private final LdapTemplate _ldapTemplate;
        private final ChalkDao _chalk;

        /**
         *
         * @param t as per SpringLDAP
         * http://static.springsource.org/spring-ldap/docs/1.3.x/reference/html/basic.html
         */
        public LDAPEnterprise (LdapTemplate t, ChalkDao chalk) {
                _ldapTemplate = t;
                _chalk = chalk;
        }

        private static final NameNotFoundException notfound = new NameNotFoundException (
                                "Not in Enterprise Directory (LDAP)");

        /**
         * @param name LDAP common name (cn) to look up
         * @return
         * @throws NameNotFoundException 
         */
        private AccountHolder findByName(final String name) throws NameNotFoundException {
        	    String filter = "(cn=" + name + ")"; // TODO: injection risk?
                final LDAPEnterprise that = this;
                @SuppressWarnings("unchecked")
                List<AccountHolder> x = (List<AccountHolder>)_ldapTemplate.search("", filter,
                        new AttributesMapper() {
                                @Override
                                public AccountHolder mapFromAttributes(Attributes attrs)
                                        throws NamingException {
                                        return new AccountHolder(that,
                                                        name,
                                                (String)attrs.get("sn").get(),
                                                (String)attrs.get("givenname").get(),
                                                (String)attrs.get("title").get(),
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
                return x.get(0);
        }

        public static final String excluded_jobcode = "24600";
        static class AccountHolder implements Agent {
                public AccountHolder(LDAPEnterprise org, String userid,
                        String surName, String givenName, String title, String mail,
                        Boolean isFaculty, String jobCode) {
                        _userid = userid;
                        _surName = surName;
                        _givenName = givenName;
                        _title = title;
                        _mail = mail;
                        _isFaculty = isFaculty;
                        _jobCode = jobCode;
                }

                private final String _userid;
                private final String _surName;
                private final String _givenName;
                private final String _title;
                private final String _mail;
                private final Boolean _isFaculty;
                private final String _jobCode;

                @Override
                public String toString() {
                	return "Agent(" + _userid + ")";
                }
                public String getUserId() {
                        return _userid;
                }

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

				@Override
				public String getTitle() {
					return _title;
				}
        }

        @Override
        public Agent affiliate(String name) throws NameNotFoundException {
                return findByName(name);
        }

        @Override
        public Agent affiliate(HttpServletRequest q) throws ServletException {
                String name = casUserId(q);
                
                AccountHolder a;
                try {
                        a = findByName(name);
                } catch (NameNotFoundException e) {
                        throw ldap_cas_disagreement;
                }

                return a;
        }
        private ServletException ldap_cas_disagreement =
                        new ServletException("Oops! LDAP and CAS disagree.");

	@Override
	public void checkFaculty(Agent supposedFaculty) throws NoPermissionException {
		AccountHolder acct;
		try {
			acct = (AccountHolder) supposedFaculty;
		} catch (ClassCastException wrongtype) {
			throw new IllegalArgumentException();
		}
		if (!acct.isQualifiedFaculty()) {
			throw notFaculty;
		}
	}

        public static class NoTraining extends NoPermissionException {
                private static final long serialVersionUID = 1L;
        }
        private final NoTraining notraining = new NoTraining();

        /**
         * 
         * @param a
         * @return
         * @throws NoTraining if training is non-existent or too old.
         * @throws IllegalArgumentException if a is not from our _org
         */
        public Date trainedThru(Agent a) throws NoTraining {
                Date training_expiration = _chalk.getChalkTrainingExpireDate(a);

                if (training_expiration == null) {
                        throw notraining;
                }

                return training_expiration;
        }


        
        /**
         * Derive a CASCap from a CAS-filtered HttpServletRequest.
         * @param request
         * @return a CASCap that gives access to the name of the authenticated CAS Principal.
         * @throws ServletException if the request's session has no CAS assertion attribute.
         */
        private String casUserId(HttpServletRequest request)  throws ServletException {
                // Rescue Assertion from un-typesafe attribute mapping.
                Assertion it = (Assertion)request.getSession().getAttribute(
                        AbstractCasFilter.CONST_CAS_ASSERTION);
                if (it == null){
                        throw noCAS;
                }

                return it.getPrincipal().getName();
        }
        
        protected static final ServletException noCAS =
                new ServletException("no CAS ticket");
}
