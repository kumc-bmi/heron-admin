/*
 * To change this template, choose Tools | Templates
 * and open the template in the editor.
 */

package edu.kumc.informatics.heron.util;

import edu.kumc.informatics.heron.dao.ChalkDao;
import edu.kumc.informatics.heron.dao.HeronDBDao;

/**
 * Modify user access policy for development mode.
 */
public class DevUserAccessData extends DBUtil {
        protected String _devUserId;

        /**
         *
         * @param h as in super
         * @param ch in super
         * @param devUserId - user id of developer
         */
        public DevUserAccessData(HeronDBDao h, ChalkDao ch, String devUserId) {
                super(h, ch);
                _devUserId = devUserId;
        }

        /**
         * @return: developer user id (from constructor)
         */
        //@Override
        //public
        private String[] getDrocIds() {
                String[] out = {_devUserId};
                return out;
        }
}
