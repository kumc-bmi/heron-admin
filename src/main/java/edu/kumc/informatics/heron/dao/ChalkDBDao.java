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

import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;
import org.springframework.dao.DataAccessException;
import org.springframework.jdbc.core.SqlOutParameter;
import org.springframework.jdbc.core.SqlParameter;
import org.springframework.jdbc.object.StoredProcedure;
import org.springframework.jdbc.core.simple.SimpleJdbcDaoSupport;

public class ChalkDBDao extends SimpleJdbcDaoSupport{
	private static Log log = LogFactory.getLog(ChalkDBDao.class);
	
	// TODO: super("java:ChalkDS");
	
	/**
	 * check if a user has been trained in CHALK
	 * @param userId
	 * @return
	 */
	@SuppressWarnings("unchecked")
	public Date getChalkTrainingExpireDate(String userId){
		Map paraMap = new HashMap();
		paraMap.put("Username", userId);
		Map aMap = new ChalkStoredProcedure(this.getDataSource()).execute(paraMap);
		return ((Date)aMap.get("HSExpirationDate"));
	}
	
	private class ChalkStoredProcedure extends StoredProcedure{
		private static final String SQL = "CheckHumanSubjectsStatus";

		ChalkStoredProcedure(DataSource dataSource) {
		      super(dataSource, SQL);
		      declareParameter(new SqlParameter("Username", Types.VARCHAR));
		      declareParameter(new SqlOutParameter("HSExpirationDate", Types.DATE));
		}
	}
}
