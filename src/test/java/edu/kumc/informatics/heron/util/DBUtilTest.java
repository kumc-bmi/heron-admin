/*
 * To change this template, choose Tools | Templates
 * and open the template in the editor.
 */

package edu.kumc.informatics.heron.util;


import org.junit.Test;
import org.junit.Assert;

import org.springframework.test.AbstractTransactionalDataSourceSpringContextTests;

import edu.kumc.informatics.heron.dao.ChalkDBDao;
import edu.kumc.informatics.heron.dao.HeronDBDao;

/**
 * TODO: rename DBUtil class
 * ref http://static.springsource.org/docs/Spring-MVC-step-by-step/part5.html#step5.5
 */
public class DBUtilTest extends AbstractTransactionalDataSourceSpringContextTests {
        @Override
        protected String[] getConfigLocations() {
                return new String[]{"classpath:test-context.xml"};
        }

        private HeronDBDao _heronDBDao;
        public void setHeronDBDao(HeronDBDao h) {
                _heronDBDao = h;
        }

        private ChalkDBDao _chalk;
        public void setChalkDBDao(ChalkDBDao c) {
                _chalk = c;
        }

        // TODO: find out why @Test didn't work here.
        public void testDrocHasAtLeastOneMemberPerOrg() {
                DBUtil it = new DBUtil(_heronDBDao, _chalk);
                int drocMemberCount = 0;
                for(String id : it.getDrocIds()){
                        drocMemberCount ++;
                        logger.info("droc member id:" + id);
                }
                logger.info("droc member count: " + drocMemberCount);
                Assert.assertTrue(drocMemberCount >= 3);
        }
}
