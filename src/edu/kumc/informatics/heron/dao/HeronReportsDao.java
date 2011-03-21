package edu.kumc.informatics.heron.dao;

import java.util.List;
import java.util.Properties;
import edu.kumc.informatics.heron.base.StaticValues;
import edu.kumc.informatics.heron.util.StaticDataUtil;

/**
 * @author dzhu
 *
 * DAO for Reports
 */
public class HeronReportsDao extends HeronDBDao{
	private Properties props = StaticDataUtil.getSoleInstance().getProperties();
	/**
	 * get all users signed system access agreement
	 * @return a list of users
	 */
	public List getHeronSystemUsers(){
		String projSchema = props.getProperty(StaticValues.PROJECT_SCHEMA);
		String sql = "select s.user_id user_id,s.user_full_name user_full_name, q.query_count query_count, p.session_count session_count "+
			"from heron.system_access_users s,"+
			"(select sa.user_id, count(ps.user_id) as query_count "+
			"from heron.system_access_users sa, "+projSchema+".QT_QUERY_MASTER ps "+
			"where sa.user_id = ps.user_id(+) "+
			"group by sa.user_id"+
			") q,"+
			"(select sa.user_id, count(ps.user_id) as session_count "+
			"from heron.system_access_users sa, pm_user_session ps "+
			"where sa.user_id = ps.user_id(+) "+
			"group by sa.user_id"+
			") p "+
			"where s.user_id = q.user_id and s.user_id = p.user_id";
		return this.getJdbcTemplate().queryForList(sql);
	}
	
	/**
	 * @see GuiUtil.getApprovedUsers
	 */
	public List getApprovedUsers(String type){
		String sql = "select user_id, research_title,expire_date,kumc_empl_flag,kuh_approval_tmst,"+
			" kumc_approval_tmst,ukp_approval_tmst from HERON.sponsorship"+
			" where access_type ='" + type + "' and kumc_approval_status='A' and kuh_approval_status='A' "+
			" and ukp_approval_status='A' order by user_id";
		return this.getJdbcTemplate().queryForList(sql);
	}
	
	/**
	 * @see GuiUtil.getQueryReportInfo
	 */
	public List getQueryReportInfo(String userId){
		String projSchema = props.getProperty(StaticValues.PROJECT_SCHEMA);
		String sql = "select name,request_xml, set_size,qri.start_date start_date,real_set_size,description "+
			"from " + projSchema+".qt_query_master qm, "+ projSchema + ".QT_QUERY_RESULT_INSTANCE qri,"+
			projSchema + ".qt_query_instance qi where qm.query_master_id=qi.query_master_id and "+
			"qi.query_instance_id=qri.query_instance_id and qm.user_id='"+ userId+"' order by name";
		return this.getJdbcTemplate().queryForList(sql);
	}
}
