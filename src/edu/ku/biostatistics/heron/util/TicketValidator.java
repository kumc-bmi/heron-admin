package edu.ku.biostatistics.heron.util;


import java.util.Iterator;
import java.util.Map;

import javax.servlet.http.HttpServletRequest;

import org.jasig.cas.client.authentication.AttributePrincipal;
import org.jasig.cas.client.validation.Assertion;
import org.jasig.cas.client.validation.Cas20ProxyTicketValidator;
import org.jasig.cas.client.validation.TicketValidationException;

public class TicketValidator {
	public final boolean validateTicket(HttpServletRequest request) {
		AttributePrincipal principal = (AttributePrincipal) request.getUserPrincipal();
		Map attributes = principal.getAttributes();

		if (attributes.size() > 0) {

			System.out.println("You have " + attributes.size() + " attributes : <br/>");
			Iterator keyIterator = attributes.keySet().iterator();

			while (keyIterator.hasNext()) {

				Object key = keyIterator.next();
				Object value = attributes.get(key);
				System.out.println("<b>" + key + "</b>" + " : " + value);
		        }
		} else {
			System.out.println("You have no attributes set");
		}
		return true;

	}
}
