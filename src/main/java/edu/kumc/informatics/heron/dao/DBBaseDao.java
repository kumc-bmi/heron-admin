/**
 * Base class for all DAO classes
 * 
 * <cite><a href="http://java.sun.com/blueprints/corej2eepatterns/Patterns/DataAccessObject.html"
 * >Core J2EE Patterns - Data Access Objects</a></cite>. Sun Microsystems Inc.. 2007-08-02.
 *
 *
 * Copyright(c) 2010-2011 <a href="http://www.kumc.edu"
 * >University of Kansas Medical Center</a>
 * by <a href="http://informatics.kumc.edu">Division of Medical Informatics</a>
 *
 */
package edu.kumc.informatics.heron.dao;

import javax.sql.DataSource;

import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.simple.SimpleJdbcDaoSupport;

import edu.kumc.informatics.heron.util.ServiceLocator;

public class DBBaseDao extends SimpleJdbcDaoSupport{
	protected final Log log = LogFactory.getLog(getClass());

	/**
	 * constructor. init SimpleJdbcTemplate.
	 * @param dataSource
	 */
        @Deprecated
	protected DBBaseDao(String dataSource){
		DataSource ds = null;
		try {
			ds = ServiceLocator.getInstance().getAppServerDataSource(dataSource);
			log.debug(ds.toString());
		} catch (Exception e2) {
			log.error("error in DBBaseDao(): " + e2.getMessage());
		} 
		this.setJdbcTemplate(new JdbcTemplate(ds));
	}
}
