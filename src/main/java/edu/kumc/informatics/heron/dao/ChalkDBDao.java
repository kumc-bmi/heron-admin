/**
 *Dao class for CHALK data access.
 * Avoid putting business logic especially gui related logic here.
 * Dongsheng Zhu
 */
package edu.kumc.informatics.heron.dao;

import java.sql.Date;
import java.sql.Types;
import java.util.HashMap;
import java.util.Map;

import javax.sql.DataSource;

import org.springframework.jdbc.core.SqlOutParameter;
import org.springframework.jdbc.core.SqlParameter;
import org.springframework.jdbc.object.StoredProcedure;
import org.springframework.jdbc.core.simple.SimpleJdbcDaoSupport;

import edu.kumc.informatics.heron.capsec.Agent;

public class ChalkDBDao extends SimpleJdbcDaoSupport{
	//private Log log = LogFactory.getLog(getClass());
		
        /**
	 * check if a user has been trained in CHALK
	 * @param userId
	 * @return expiration date of HSC training, or null if none on file
         * @throws NotOwnerException
	 */
	public Date getChalkTrainingExpireDate(Agent who) {
	        return new ChalkStoredProcedure(this.getDataSource()).getTrainingExpiration(who);
	}

	private class ChalkStoredProcedure extends StoredProcedure{
		private static final String SQL = "CheckHumanSubjectsStatus";
                private static final String USERNAME = "Username";
                private static final String EXPIRATION = "HSExpirationDate";

		ChalkStoredProcedure(DataSource dataSource) {
		      super(dataSource, SQL);
		      declareParameter(new SqlParameter(USERNAME, Types.VARCHAR));
		      declareParameter(new SqlOutParameter(EXPIRATION, Types.DATE));
		}
		
                Date getTrainingExpiration(Agent who) {
                        Map<String, String> paraMap = new HashMap<String, String>();
                        paraMap.put(USERNAME, who.getUserId());
                        @SuppressWarnings("rawtypes")
                        Map aMap = execute(paraMap);
                        return((Date) aMap.get(EXPIRATION));
                }
	}
}
