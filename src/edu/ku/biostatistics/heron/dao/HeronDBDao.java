package edu.ku.biostatistics.heron.dao;

import java.util.List;

import javax.sql.DataSource;

import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;
import org.springframework.dao.DataAccessException;
import org.springframework.jdbc.core.simple.SimpleJdbcTemplate;
import org.springframework.jdbc.core.support.JdbcDaoSupport;

import edu.harvard.i2b2.common.exception.I2B2DAOException;
import edu.harvard.i2b2.common.exception.I2B2Exception;
import edu.ku.biostatistics.heron.util.ServiceLocator;

public class HeronDBDao extends JdbcDaoSupport{


	private static Log log = LogFactory.getLog(HeronDBDao.class);
	private ServiceLocator serviceLocator = ServiceLocator.getInstance();

	private SimpleJdbcTemplate jt;

	public HeronDBDao() throws Exception{
		DataSource ds = null;
		try {
			ds = serviceLocator.getAppServerDataSource("java:PMBootStrapDS");
			log.debug(ds.toString());
		} catch (Exception e2) {
			log.error("bootstrap ds failure: " + e2.getMessage());
			throw e2;
		} 
		this.jt = new SimpleJdbcTemplate(ds);
	}
	
	@SuppressWarnings("unchecked")
	public List getUserData(String userId) throws I2B2Exception, I2B2DAOException { 
		String sql =  "select * from pm_user_data where user_id=?";
		//		log.info(sql + domainId + projectId + ownerId);
		List queryResult = null;
		try {
			queryResult = jt.queryForList(sql, userId);
		} catch (DataAccessException e) {
			log.error(e.getMessage());
			throw new I2B2DAOException("Database error");
		}
		return queryResult;	
	}
}
