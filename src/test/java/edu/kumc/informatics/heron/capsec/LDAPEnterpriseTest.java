/* Copyright (c) 2011 The University of Kansas Medical Center
 * http://informatics.kumc.edu/ */

package edu.kumc.informatics.heron.capsec;

import com.sun.org.apache.xpath.internal.NodeSet;
import java.io.StringReader;
import java.util.Hashtable;
import java.util.logging.Level;
import java.util.logging.Logger;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import javax.naming.Binding;
import javax.naming.Context;
import javax.naming.Name;
import javax.naming.NameClassPair;
import javax.naming.NameParser;
import javax.naming.NamingEnumeration;
import javax.naming.directory.Attributes;
import javax.naming.directory.DirContext;
import javax.naming.directory.ModificationItem;
import javax.naming.directory.SearchControls;
import javax.naming.directory.SearchResult;
import javax.xml.xpath.XPath;
import javax.xml.xpath.XPathConstants;
import javax.xml.xpath.XPathExpressionException;
import javax.xml.xpath.XPathFactory;

import org.junit.Test;
import org.junit.Assert;

import org.springframework.ldap.NamingException;
import org.springframework.ldap.core.ContextSource;
import org.xml.sax.InputSource;

public class LDAPEnterpriseTest {

        public static final String mockData = "/mockDirectory.html";
        public static final XPath xpath = XPathFactory.newInstance().newXPath();

        @Test
        public void parseSomething() throws XPathExpressionException {
                InputSource src =
                        new InputSource(getClass().getResourceAsStream(mockData));
                String actual = xpath.evaluate(
                        "/html/head/title", src);
                Assert.assertEquals("hi there", actual);
        }


        public static class HCardSource implements ContextSource {
                @Override
                public DirContext getReadOnlyContext() throws NamingException {
                        InputSource hCardSrc =
                                new InputSource(getClass().getResourceAsStream(mockData));
                        return new HCardContext(hCardSrc);
                }

                @Override
                public DirContext getReadWriteContext() throws NamingException {
                        throw new UnsupportedOperationException("Not supported yet.");
                }

                /**
                 * I'm not sure this is faithful to the interface...
                 * @param u
                 * @param p
                 * @return
                 * @throws NamingException 
                 */
                @Override
                public DirContext getContext(String u, String p) throws NamingException {
                        return getReadOnlyContext();
                }
                
        }
        
        public static class HCardContext implements DirContext {
                private final InputSource _src;
                HCardContext(InputSource src) {
                        _src = src;
                }

                private static final Pattern cnFilter = Pattern.compile("\\(cn=([^\\)]+)\\)");

                @Override
                public NamingEnumeration<SearchResult> search(String name, String filter, SearchControls cons) throws javax.naming.NamingException {
                        Matcher m = cnFilter.matcher(filter);
                        if (m.matches()) {
                                String pathToId = "//*[@id=\"" + m.group(1) + "\"]";
                                try {
                                        NodeSet cards = (NodeSet) xpath.evaluate(pathToId, _src, XPathConstants.NODESET);
                                        return new NamingEnumeration<SearchResult>(){
                                                @Override
                                                public Boolean hasMore() {
                                                        return false; //@@TODO
                                                }
                                                @Override
                                                public void close() {
                                                        // noop
                                                }
                                        };
                                } catch (XPathExpressionException ex) {
                                        throw new javax.naming.NamingException(ex.getMessage());
                                }
                        }
                }


                @Override
                public Attributes getAttributes(Name name) throws javax.naming.NamingException {
                        throw new UnsupportedOperationException("Not supported yet.");
                }

                @Override
                public Attributes getAttributes(String name) throws javax.naming.NamingException {
                        throw new UnsupportedOperationException("Not supported yet.");
                }

                @Override
                public Attributes getAttributes(Name name, String[] attrIds) throws javax.naming.NamingException {
                        throw new UnsupportedOperationException("Not supported yet.");
                }

                @Override
                public Attributes getAttributes(String name, String[] attrIds) throws javax.naming.NamingException {
                        throw new UnsupportedOperationException("Not supported yet.");
                }

                @Override
                public void modifyAttributes(Name name, int mod_op, Attributes attrs) throws javax.naming.NamingException {
                        throw new UnsupportedOperationException("Not supported.");
                }

                @Override
                public void modifyAttributes(String name, int mod_op, Attributes attrs) throws javax.naming.NamingException {
                        throw new UnsupportedOperationException("Not supported.");
                }

                @Override
                public void modifyAttributes(Name name, ModificationItem[] mods) throws javax.naming.NamingException {
                        throw new UnsupportedOperationException("Not supported.");
                }

                @Override
                public void modifyAttributes(String name, ModificationItem[] mods) throws javax.naming.NamingException {
                        throw new UnsupportedOperationException("Not supported.");
                }

                @Override
                public void bind(Name name, Object obj, Attributes attrs) throws javax.naming.NamingException {
                        throw new UnsupportedOperationException("Not supported.");
                }

                @Override
                public void bind(String name, Object obj, Attributes attrs) throws javax.naming.NamingException {
                        throw new UnsupportedOperationException("Not supported.");
                }

                @Override
                public void rebind(Name name, Object obj, Attributes attrs) throws javax.naming.NamingException {
                        throw new UnsupportedOperationException("Not supported.");
                }

                @Override
                public void rebind(String name, Object obj, Attributes attrs) throws javax.naming.NamingException {
                        throw new UnsupportedOperationException("Not supported.");
                }

                @Override
                public DirContext createSubcontext(Name name, Attributes attrs) throws javax.naming.NamingException {
                        throw new UnsupportedOperationException("Not supported.");
                }

                @Override
                public DirContext createSubcontext(String name, Attributes attrs) throws javax.naming.NamingException {
                        throw new UnsupportedOperationException("Not supported.");
                }

                @Override
                public DirContext getSchema(Name name) throws javax.naming.NamingException {
                        throw new UnsupportedOperationException("Not supported.");
                }

                @Override
                public DirContext getSchema(String name) throws javax.naming.NamingException {
                        throw new UnsupportedOperationException("Not supported.");
                }

                @Override
                public DirContext getSchemaClassDefinition(Name name) throws javax.naming.NamingException {
                        throw new UnsupportedOperationException("Not supported.");
                }

                @Override
                public DirContext getSchemaClassDefinition(String name) throws javax.naming.NamingException {
                        throw new UnsupportedOperationException("Not supported.");
                }

                @Override
                public NamingEnumeration<SearchResult> search(Name name, Attributes matchingAttributes, String[] attributesToReturn) throws javax.naming.NamingException {
                        throw new UnsupportedOperationException("Not supported yet.");
                }

                @Override
                public NamingEnumeration<SearchResult> search(String name, Attributes matchingAttributes, String[] attributesToReturn) throws javax.naming.NamingException {
                        throw new UnsupportedOperationException("Not supported yet.");
                }

                @Override
                public NamingEnumeration<SearchResult> search(Name name, Attributes matchingAttributes) throws javax.naming.NamingException {
                        throw new UnsupportedOperationException("Not supported yet.");
                }

                @Override
                public NamingEnumeration<SearchResult> search(String name, Attributes matchingAttributes) throws javax.naming.NamingException {
                        throw new UnsupportedOperationException("Not supported yet.");
                }

                @Override
                public NamingEnumeration<SearchResult> search(Name name, String filter, SearchControls cons) throws javax.naming.NamingException {
                        throw new UnsupportedOperationException("Not supported yet.");
                }

                @Override
                public NamingEnumeration<SearchResult> search(Name name, String filterExpr, Object[] filterArgs, SearchControls cons) throws javax.naming.NamingException {
                        throw new UnsupportedOperationException("Not supported yet.");
                }

                @Override
                public NamingEnumeration<SearchResult> search(String name, String filterExpr, Object[] filterArgs, SearchControls cons) throws javax.naming.NamingException {
                        throw new UnsupportedOperationException("Not supported yet.");
                }

                @Override
                public Object lookup(Name name) throws javax.naming.NamingException {
                        throw new UnsupportedOperationException("Not supported yet.");
                }

                @Override
                public Object lookup(String name) throws javax.naming.NamingException {
                        throw new UnsupportedOperationException("Not supported yet.");
                }

                @Override
                public void bind(Name name, Object obj) throws javax.naming.NamingException {
                        throw new UnsupportedOperationException("Not supported yet.");
                }

                @Override
                public void bind(String name, Object obj) throws javax.naming.NamingException {
                        throw new UnsupportedOperationException("Not supported yet.");
                }

                @Override
                public void rebind(Name name, Object obj) throws javax.naming.NamingException {
                        throw new UnsupportedOperationException("Not supported yet.");
                }

                @Override
                public void rebind(String name, Object obj) throws javax.naming.NamingException {
                        throw new UnsupportedOperationException("Not supported yet.");
                }

                @Override
                public void unbind(Name name) throws javax.naming.NamingException {
                        throw new UnsupportedOperationException("Not supported yet.");
                }

                @Override
                public void unbind(String name) throws javax.naming.NamingException {
                        throw new UnsupportedOperationException("Not supported yet.");
                }

                @Override
                public void rename(Name oldName, Name newName) throws javax.naming.NamingException {
                        throw new UnsupportedOperationException("Not supported yet.");
                }

                @Override
                public void rename(String oldName, String newName) throws javax.naming.NamingException {
                        throw new UnsupportedOperationException("Not supported yet.");
                }

                @Override
                public NamingEnumeration<NameClassPair> list(Name name) throws javax.naming.NamingException {
                        throw new UnsupportedOperationException("Not supported yet.");
                }

                @Override
                public NamingEnumeration<NameClassPair> list(String name) throws javax.naming.NamingException {
                        throw new UnsupportedOperationException("Not supported yet.");
                }

                @Override
                public NamingEnumeration<Binding> listBindings(Name name) throws javax.naming.NamingException {
                        throw new UnsupportedOperationException("Not supported yet.");
                }

                @Override
                public NamingEnumeration<Binding> listBindings(String name) throws javax.naming.NamingException {
                        throw new UnsupportedOperationException("Not supported yet.");
                }

                @Override
                public void destroySubcontext(Name name) throws javax.naming.NamingException {
                        throw new UnsupportedOperationException("Not supported yet.");
                }

                @Override
                public void destroySubcontext(String name) throws javax.naming.NamingException {
                        throw new UnsupportedOperationException("Not supported yet.");
                }

                @Override
                public Context createSubcontext(Name name) throws javax.naming.NamingException {
                        throw new UnsupportedOperationException("Not supported yet.");
                }

                @Override
                public Context createSubcontext(String name) throws javax.naming.NamingException {
                        throw new UnsupportedOperationException("Not supported yet.");
                }

                @Override
                public Object lookupLink(Name name) throws javax.naming.NamingException {
                        throw new UnsupportedOperationException("Not supported yet.");
                }

                @Override
                public Object lookupLink(String name) throws javax.naming.NamingException {
                        throw new UnsupportedOperationException("Not supported yet.");
                }

                @Override
                public NameParser getNameParser(Name name) throws javax.naming.NamingException {
                        throw new UnsupportedOperationException("Not supported yet.");
                }

                @Override
                public NameParser getNameParser(String name) throws javax.naming.NamingException {
                        throw new UnsupportedOperationException("Not supported yet.");
                }

                @Override
                public Name composeName(Name name, Name prefix) throws javax.naming.NamingException {
                        throw new UnsupportedOperationException("Not supported yet.");
                }

                @Override
                public String composeName(String name, String prefix) throws javax.naming.NamingException {
                        throw new UnsupportedOperationException("Not supported yet.");
                }

                @Override
                public Object addToEnvironment(String propName, Object propVal) throws javax.naming.NamingException {
                        throw new UnsupportedOperationException("Not supported yet.");
                }

                @Override
                public Object removeFromEnvironment(String propName) throws javax.naming.NamingException {
                        throw new UnsupportedOperationException("Not supported yet.");
                }

                @Override
                public Hashtable<?, ?> getEnvironment() throws javax.naming.NamingException {
                        throw new UnsupportedOperationException("Not supported yet.");
                }

                @Override
                public void close() throws javax.naming.NamingException {

                }

                @Override
                public String getNameInNamespace() throws javax.naming.NamingException {
                        throw new UnsupportedOperationException("Not supported yet.");
                }
                
        }
}

