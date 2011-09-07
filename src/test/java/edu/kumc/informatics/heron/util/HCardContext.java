/*
 * To change this template, choose Tools | Templates
 * and open the template in the editor.
 */
package edu.kumc.informatics.heron.util;

import java.io.IOException;
import java.util.Hashtable;
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

import org.w3c.dom.Node;
import org.w3c.dom.NodeList;
import org.xml.sax.InputSource;

/**
 * Simulate an simple LDAP-like naming context based on
 * <a href="http://microformats.org/wiki/hcard">hCard</a> hCard data.
 * 
 * @author connolly
 */
public abstract class HCardContext implements DirContext {
    public static final XPath xpath = XPathFactory.newInstance().newXPath();
    private final Logger logger = Logger.getLogger(getClass().getName());
        
    private final Node _root;
    protected HCardContext(InputSource xmlsrc) throws XPathExpressionException {
	    _root = (Node) xpath.evaluate("/", xmlsrc, XPathConstants.NODE);
    }


    /**
     * Find hCard elements by id.
     * 
     * Note: we don't actually look for class="hCard".
     * 
     * @param id
     * @return a NodeList of all elements with matching id attributes
     * @throws XPathExpressionException
     */
    public NodeList findCards(String id) {
	    logger.entering(getClass().getName(), "findCards");
	//for test code, we assume id syntax is OK
        String pathToId = "//*[@id=\"" + id + "\"]";
        try {
	        return (NodeList) xpath.evaluate(pathToId, _root, XPathConstants.NODESET);
        } catch (XPathExpressionException e) {
        	logger.severe("error evaluating: " + pathToId);
        	throw new RuntimeException(e);
//        	throw new RuntimeException("design-time xpath error:" + e.getMessage() +
//        			(e.getCause() == null ? "" : "cause: " +e.getCause().getMessage()));
        }
    }

    /**
     * Get an hCard property value.
     * 
     * @param hcard
     * @param hcardClass
     * @return text of child of hcard with matching class attribute
     */
    public String getHCardProperty(Node hcard, String hcardClass) {
            String findByClass = ".//*[@class='" + hcardClass + "']/text()";
            String value;
            try {
            	value = xpath.evaluate(findByClass, hcard);
            } catch (XPathExpressionException ex) {
            	throw new RuntimeException(
            			"Bad XPath defined at design time:" + findByClass,
            			ex);
            }
            return value;
    }

    public abstract Attributes cardAttributes(Node hcard);

    protected class CardEnumeration implements NamingEnumeration<SearchResult> {

        private String _name;
        private final NodeList _cards;
        private final int _qty;
        private int _i;

        CardEnumeration(String name, NodeList cards, int qty) {
            _name = name;
            _cards = cards;
            _qty = qty;
            _i = 0;
        }

        @Override
        public boolean hasMore() {
            return _i < _qty;
        }

        @Override
        public SearchResult next() {
            Node card = _cards.item(_i);
            _i++;
            return new SearchResult(_name, card,
                    cardAttributes(card));
        }

        // umm... what are these?
        @Override
        public boolean hasMoreElements() {
            return false;
        }

        @Override
        public SearchResult nextElement() {
            return null;
        }

        @Override
        public void close() {
            // noop
        }
    }

    private static final Pattern cnFilter = Pattern.compile("\\(cn=([^\\)]+)\\)");

    @Override
    public NamingEnumeration<SearchResult> search(final String name, String filter, SearchControls cons) throws javax.naming.NamingException {
        Matcher m = cnFilter.matcher(filter);
        if (m.matches()) {
            String target = m.group(1);
            final NodeList cards = findCards(target);
            return new CardEnumeration(target, cards, cards.getLength());
        } else {
            logger.info("search: regexp failed to get name from: " + filter);
            return new CardEnumeration(name, null, 0);
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
