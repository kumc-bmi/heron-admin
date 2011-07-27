/*
 * To change this template, choose Tools | Templates
 * and open the template in the editor.
 */

package edu.kumc.informatics.heron.util;

import org.junit.Test;
import org.junit.Assert;
import org.junit.runner.RunWith;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.AbstractTransactionalDataSourceSpringContextTests;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.SpringJUnit4ClassRunner;

import edu.kumc.informatics.heron.dao.ChalkDBDao;
import edu.kumc.informatics.heron.dao.HeronDBDao;

/**
 * TODO: rename DBUtil class
 * ref http://static.springsource.org/docs/Spring-MVC-step-by-step/part5.html#step5.5
 *
 * TODO: separate unit tests from integration tests; try spring's:
 * @IfProfileValue(name="test-groups", values={"unit-tests", "integration-tests"})
 */

@RunWith(SpringJUnit4ClassRunner.class)
@ContextConfiguration(locations={"classpath:heron-integration-context.xml"})
public class DBUtilTest extends AbstractTransactionalDataSourceSpringContextTests {
        @Autowired
        private HeronDBDao _heronDBDao;

        @Autowired
        private ChalkDBDao _chalk;

        @Test
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
