package edu.ku.biostatistics.heron.util;

import org.springframework.beans.factory.BeanFactory;
import org.springframework.beans.factory.access.BeanFactoryLocator;
import org.springframework.beans.factory.access.BeanFactoryReference;
import org.springframework.beans.factory.access.SingletonBeanFactoryLocator;
import org.springframework.beans.factory.config.PropertiesFactoryBean;
import org.springframework.core.io.ClassPathResource;

import java.io.IOException;

import java.util.Collections;
import java.util.HashMap;
import java.util.Map;
import java.util.Properties;

import javax.ejb.EJBLocalHome;

import javax.jms.Queue;
import javax.jms.QueueConnectionFactory;

import javax.naming.Context;
import javax.naming.InitialContext;
import javax.naming.NamingException;

import javax.sql.DataSource;


/**
 * ServiceLocator class to get reference to resource like EJB, JMS, Datasource etc.
 * This is singleton class and caches resources.
 * @author rk903
 */
public class ServiceLocator {
    //datasource bean name
    public static String DATASOURCE_BEAN_NAME = "dataSource";

    //default client property file name
    public static final String CLIENT_PROPERTY_CONFIG_LOCATION = "client.properties";
    private static BeanFactory beanFactory = null;
    private static Properties clientProperties = null;

    //to make this class singleton
    private static ServiceLocator thisInstance;

    static {
        try {
            thisInstance = new ServiceLocator();
        } catch (Exception se) {
            System.err.println(se);
            se.printStackTrace(System.err);
        }
    }

    private InitialContext ic;

    //used to hold references to EJBHomes/JMS Resources for re-use
    private Map cache;

    private ServiceLocator() throws Exception {
        try {
            ic = new InitialContext();
            cache = Collections.synchronizedMap(new HashMap());
        } catch (NamingException ne) {
            throw new Exception(ne);
        } catch (Exception e) {
            throw new Exception(e);
        }
    }

    public static ServiceLocator getInstance() {
        return thisInstance;
    }

    public  BeanFactory getSpringFactory() {
        if (beanFactory == null) {
            BeanFactoryLocator beanFactoryLoc = SingletonBeanFactoryLocator.getInstance();
            BeanFactoryReference beanFactoryRef = beanFactoryLoc.useBeanFactory(
                    "edu.harvard.i2b2Core2");
            beanFactory = beanFactoryRef.getFactory();
        }

        return beanFactory;
    }

    

    
    /**
      * Get the database datasource.
      * @param dataSourceName
      * @return The data source
      * @throws MPGException
      */
    public DataSource getAppServerDataSource(String dataSourceName)
        throws Exception {
        javax.sql.DataSource dataSource = null;

        try {
            Context context = new InitialContext();
            dataSource = (javax.sql.DataSource) context.lookup(dataSourceName);
        } catch (Exception ex) {
            ex.printStackTrace();
            throw new Exception("Servicelocator.getDBDataSource", ex);
        }

        return dataSource;
    }

    /**
     * Function to get client's property context.
     * @return PropertyUtil
     */
    public static Properties getClientProperty() throws Exception {
        if (clientProperties == null) {
            clientProperties = getProperties(CLIENT_PROPERTY_CONFIG_LOCATION);
        }

        return clientProperties;
    }

    /**
     * Return Properties object, for input property file.
     * @param propFileName
     * @return java.util.Properties
     * @throws I2B2Exception
     */
    public static Properties getProperties(String propFileName)
        throws Exception {
        PropertiesFactoryBean pfb = new PropertiesFactoryBean();
        pfb.setLocation(new ClassPathResource(propFileName));

        Properties props = null;

        try {
            pfb.afterPropertiesSet();
            props = (Properties) pfb.getObject();
        } catch (IOException ioEx) {
            throw new Exception("IOException " + ioEx.getMessage(), ioEx);
        }

        return props;
    }

    /**
    * @return the factory for the factory to get queue connections from
    */
    public QueueConnectionFactory getQueueConnectionFactory(
        String qConnFactoryName) throws Exception {
        QueueConnectionFactory factory = null;

        try {
            if (cache.containsKey(qConnFactoryName)) {
                factory = (QueueConnectionFactory) cache.get(qConnFactoryName);
            } else {
                factory = (QueueConnectionFactory) ic.lookup(qConnFactoryName);
                cache.put(qConnFactoryName, factory);
            }
        } catch (NamingException ne) {
            throw new Exception(ne);
        } catch (Exception e) {
            throw new Exception(e);
        }

        return factory;
    }

    /**
     * @return the Queue Destination to send messages to
     */
    public Queue getQueue(String queueName) throws Exception {
        Queue queue = null;

        try {
            if (cache.containsKey(queueName)) {
                queue = (Queue) cache.get(queueName);
            } else {
                queue = (Queue) ic.lookup(queueName);
                cache.put(queueName, queue);
            }
        } catch (NamingException ne) {
            throw new Exception(ne);
        } catch (Exception e) {
            throw new Exception(e);
        }

        return queue;
    }

    /**
     * will get the ejb Local home factory. If this ejb home factory has already been
     * clients need to cast to the type of EJBHome they desire
     *
     * @return the EJB Home corresponding to the homeName
     */
    public EJBLocalHome getLocalHome(String jndiHomeName)
        throws Exception {
        EJBLocalHome home = null;

        try {
            if (cache.containsKey(jndiHomeName)) {
                home = (EJBLocalHome) cache.get(jndiHomeName);
            } else {
                home = (EJBLocalHome) ic.lookup(jndiHomeName);
                cache.put(jndiHomeName, home);
            }
        } catch (NamingException ne) {
            throw new Exception(ne);
        } catch (Exception e) {
            throw new Exception(e);
        }

        return home;
    }
}
