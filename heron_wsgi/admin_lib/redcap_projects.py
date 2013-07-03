'''redcap_projects.py -- Choosing and preparing the i2b2 project for the user
'''

import logging

from sqlalchemy import text

log = logging.getLogger(__name__)
CONFIG_SECTION = 'i2b2md'


class REDCap_projects():
    def __init__(self):
        pass

    def pick_project(self, uid, rc_pids, pmsm, mdsm,
                     Project, UserRole, UserSession,
                     i2b2_pids=('REDCap_1', 'REDCap_2',
                                'REDCap_3', 'REDCap_4', 'REDCap_5')):
        '''Pick an i2b2 redcap project for the user
        '''
        rc_pids.sort()
        proj_desc = 'redcap'
        for pid in rc_pids:
            proj_desc += '_' + str(pid)
        log.debug('proj_desc in pick_project: %s', proj_desc)
        i2b2_pid = ''

        #is there already an existing project with this redcap data?
        if proj_desc:
            rs = pmsm.query(Project).filter_by(
                    project_description=proj_desc).order_by(
                                        Project.project_id.desc()).first()
            log.debug('rs in pick_project: %s', rs)
            if rs:
                log.debug('There is an existing project with this data')
                i2b2_pid = rs.project_id

        x = []
        for rs in pmsm.query(UserRole).all():
            x.append(rs.project_id)
        empty_pid_list = list(set(i2b2_pids).difference(set(x)))
        #set(x) will remove duplicates. So no need for distinct.
        empty_pid = ''
        if empty_pid_list:
            empty_pid_list.sort()
            empty_pid = empty_pid_list[0]
            log.debug('We found an empty project')

        if i2b2_pid and i2b2_pid in i2b2_pids:
            #Can we overload?
            return i2b2_pid
        elif empty_pid and empty_pid in i2b2_pids:
            #A project that has never been used
            return empty_pid
