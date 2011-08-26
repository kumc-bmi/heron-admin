package edu.kumc.informatics.heron.base;

/**
 * @deprecated TODO: refactor to reduce coupling
 * keep URL constants (remove .jsp), move to servlet package
 */
public interface StaticValues {
	String CHALK_URL = "chalk_url";
	String CAS_LOGIN_URL = "cas_login_url";
	String I2B2_CLIENT_SERVICE = "i2b2_client_service";
	@Deprecated
	String USER_NAME = "user_name";
	String NOT_QUALIFIED_URL = "not_qualified.jsp";
	String NOT_TRAINED_URL = "not_trained.jsp";
	String SAA_URL = "system_access_agreement.jsp";
	String GEN_DISPLAY_URL = "gen_display.jsp";
	String SPONSOR_URL = "sponsorship.jsp";
	String DATA_USAGE_URL = "data_usage_agreement.jsp";
	String DENIED_URL = "index.jsp";
	@Deprecated
	String VAL_MESSAGE = "VAL_MESSAGE";
	String VAL_ERR_URL = "validation_error.jsp";
	String USER_PROJ = "user_project";
	@Deprecated
	String USER_FULL_NAME = "full_name";
	@Deprecated
	String USER_TITLE = "user_title";
	@Deprecated
	String[] userRoles = new String[]{"USER","DATA_OBFSC"};
	@Deprecated
	String LDAP_PROV_URL = "ldap_prov_url";
	@Deprecated
	String LDAP_PRINCIPAL = "ldap_principal";
	@Deprecated
	String LDAP_CREDENTIAL = "ldap_credential";
	String HOME_URL = "index.jsp";
	String RAVEN_URL = "raven_url";
	String DISCLAIMER_URL ="disclaimer.jsp";
	@Deprecated
	String PROJECT_SCHEMA="project_schema";
        @Deprecated
	String USER_ROLES_LIST = "USER_ROLES_LIST";
	String TERM_URL = "term_heron_users.jsp";
	String TERM_ACTION = "Terminate";
}
