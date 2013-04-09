'''redcap_projects.py -- Choosing and preparing the i2b2 project for the user
'''

import logging

from sqlalchemy import text

log = logging.getLogger(__name__)
CONFIG_SECTION = 'i2b2md'


class REDCap_projects():
    def __init__(self):
        pass

    def _sql_vacate(self):
        return text('''SELECT MAX(last_login) last_login,
  project_id
FROM
  (SELECT prd.project_id,
    pru.user_id ,
    pus.last_login
  FROM
    (SELECT project_id
    FROM i2b2pm.pm_project_data
    WHERE project_id LIKE 'REDCap%'
    ) prd
  LEFT JOIN
    (SELECT DISTINCT user_id, project_id FROM i2b2pm.pm_project_user_roles
    ) pru
  ON pru.project_id = prd.project_id
  LEFT JOIN
    (SELECT MAX(expired_date) AS last_login,
      user_id
    FROM I2B2PM.pm_user_session
    GROUP BY user_id
    ) pus
  ON pus.user_id = pru.user_id
  )
GROUP BY project_id ) WHERE last_login < sysdate''')

    def create_metadata(self, i2b2_pid, rc_pids):
        '''create metadata in the chose i2b2 project
        '''
        sql_clean_ta = text('''TRUNCATE TABLE ''' + i2b2_pid + '''.TABLE_ACCESS
                            ''')
        sql_ta = text('''insert into ''' + i2b2_pid + '''.TABLE_ACCESS
 select * from blueheronmetadata.table_access ''')
        sql_ht = text('''CREATE OR REPLACE VIEW ''' + i2b2_pid + '''.HERON_TERMS
 select * from BLUEHERONMETADATA.HERON_TERMS ''')

        for rc_pid in rc_pids:
            #http://stackoverflow.com/questions/2179493/adding-backslashes-without-escaping-python
            rc_fullname = '\'\\i2b2\\redcap\\' + rc_pid + '\\%\''
            sql_ta += text('''union all select * from
blueheronmetadata.table_access_redcap
where c_fullname like ''' + rc_fullname)
            sql_ht += text('''UNION ALL select * from
BLUEHERONMETADATA.REDCAP_TERMS
WHERE C_FULLNAME LIKE ''' + rc_fullname)
        self._mdsm.execute(sql_clean_ta)
        self._mdsm.execute(sql_ta)
        self._mdsm.execute(sql_ht)

    def revoke_access(self, i2b2_pid):
        '''If we are re-purposing an i2b2 project that is not currently used
        revoke user access to it
        '''
        sql_revoke = text('''delete from i2b2pm.pm_project_user_roles
        where project_id = :pid''')
        self._ds.execute(sql_revoke, pid=i2b2_pid)

    def pick_project(self, uid, rc_pids, pmsm, mdsm,
                     Project, UserRole, UserSession,
                     i2b2_pids=('REDCap1', 'REDCap2',
                                'REDCap3', 'REDCap4', 'REDCap5')):
        '''Pick an i2b2 redcap project for the user
        '''
        rc_pids.sort()
        proj_desc = 'redcap_'
        for pid in rc_pids:
            proj_desc += str(pid)
        log.debug('proj_desc in pick_project: %s', proj_desc)

        i2b2_pid = ''

        #is there already an existing project with this redcap data?
        if proj_desc:
            rs = pmsm.query(Project).filter_by(project_description=proj_desc).first()
            log.debug('rs in pick_project: %s', rs)
            if rs:
                log.debug('There is an existing project with this data')
                i2b2_pid = rs.project_id

        x = []
        for rs in pmsm.query(UserRole).all():
            x.append(rs.project_id)
        empty_pid_list = list(set(i2b2_pids).difference(set(x)))
        #set(x) will remove duplicates. So no need for distinct.
        if empty_pid_list:
            empty_pid = empty_pid_list[0]
            log.debug('We found an empty project')

        #TODO: to pick and vacate a project
        #vacate_pid = self._ds.execute(self._sql_vacate()).fetchone()['project_id']
        #vacate_pid = self._ds.query(UserRole).join((UserSession,
        #                UserRole.user_id == UserSession.user_id))
        #http://docs.sqlalchemy.org/en/rel_0_7/orm/query.html

        if i2b2_pid and i2b2_pid in i2b2_pids:
            #Can we overload?
            return i2b2_pid
        elif empty_pid and empty_pid in i2b2_pids:
        #A project that has never been used
            #self.create_metadata(empty_pid, rc_pids)
            return empty_pid

        '''elif vacate_pid and vacate_pid in i2b2_pids:
        #Vacate a project that is not currently in use
            self.create_metadata(vacate_pid, rc_pids)
            self.revoke_access(vacate_pid)
            return vacate_pid
        '''
