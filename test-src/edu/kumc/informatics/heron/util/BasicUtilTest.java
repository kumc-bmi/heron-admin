package edu.kumc.informatics.heron.util;

import static org.junit.Assert.*;

import org.junit.Test;

public class BasicUtilTest extends BasicUtil{
	@Test
	public void testLdapCheck(){
		assertTrue(this.ldapCheck("rwaitman").equals(""));
	}
	
	@Test
	public void testLdapCheck2(){
		assertFalse(this.ldapCheck(new String[]{"rwaitman","tester"}).equals(""));
	}
}
