/**
 * properties file reader
 * 
 * dongsheng zhu
 */
package edu.ku.biostatistics.heron.util;

import java.io.IOException;
import java.util.Properties;
import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;

public class StaticDataUtil {
	private static Properties properties = null;
	protected final Log log = LogFactory.getLog(getClass());
	private static StaticDataUtil soleInstance;
	
	public Properties getProperties() {
		if (properties == null) {
			// Read properties file.
			properties = new Properties();
			try {
				properties.load(getClass().getResourceAsStream(("/configs.properties")));
			} catch (IOException e) {
				log.error("error at reading property file");
			}
		}
		return properties;
	}
	
	public static StaticDataUtil getSoleInstance()
	{
		if(soleInstance==null)
			soleInstance = new StaticDataUtil();
		return soleInstance;
	}
}
