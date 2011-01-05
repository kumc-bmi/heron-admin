/**
 * Base class for all DAO classes
 * 
 * D. Zhu
 */
package edu.ku.biostatistics.heron.dao;

import javax.sql.DataSource;

import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;
import org.springframework.jdbc.core.simple.SimpleJdbcTemplate;
import org.springframework.jdbc.core.support.JdbcDaoSupport;

import edu.ku.biostatistics.heron.util.ServiceLocator;

public class DBBaseDao extends JdbcDaoSupport{
	private static Log log = LogFactory.getLog(DBBaseDao.class);
	private SimpleJdbcTemplate sJdbcTemplate;
	
	public SimpleJdbcTemplate getSJdbcTemplate() {
		return sJdbcTemplate;
	}

	public void setSJdbcTemplate(SimpleJdbcTemplate jdbcTemplate) {
		this.sJdbcTemplate = jdbcTemplate;
	}

	public DBBaseDao(){}
	
	/**
	 * constructor. init SimpleJdbcTemplate.
	 * @param dataSource
	 */
	public DBBaseDao(String dataSource){
		DataSource ds = null;
		try {
			ds = ServiceLocator.getInstance().getAppServerDataSource(dataSource);
			log.debug(ds.toString());
		} catch (Exception e2) {
			log.error("error in DBBaseDao(): " + e2.getMessage());
		} 
		this.sJdbcTemplate = new SimpleJdbcTemplate(ds);
	}
}
