/**
 * properties loader
 * 
 * @author dongsheng zhu
 */
package edu.kumc.informatics.heron.util;

import java.io.InputStream;
import java.io.IOException;
import java.io.FileNotFoundException;
import java.util.Properties;

public class StaticDataUtil {
        /* The Java spec guarantees that the static initialiser will be
         * executed only once, at class load time.
         * http://c2.com/cgi/wiki?JavaSingleton
         */
	private static StaticDataUtil soleInstance = new StaticDataUtil();

        private Properties properties = null;

        /**
         * HERON properties are taken from /config.properties.
         */
        public static final String propertyResourcePath = "/configs.properties";
        /**
         * todo: replace this with type-safe access to properties based on an enumeration,
         *       or with spring/bean-based config.
         * @return
         */
        @Deprecated
	public Properties getProperties() {
		if (properties == null) {
                        InputStream s = getClass().getResourceAsStream(propertyResourcePath);
                        if (s == null) {
                                throw new Error("build problem: missing procperties",
                                        new FileNotFoundException(propertyResourcePath));
                        }
                        Properties p = new Properties();
                        try {
                                p.load(s);
                        } catch (IOException e) {
                                throw new Error("build problem: cannot load properties", e);
                        }
                        properties = p;
		}
                return properties;
	}

        @Deprecated
	public static StaticDataUtil getSoleInstance()
	{
		return soleInstance;
	}
}
