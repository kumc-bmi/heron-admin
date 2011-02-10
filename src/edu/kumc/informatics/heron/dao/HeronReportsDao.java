package edu.kumc.informatics.heron.dao;

import java.util.List;

/**
 * @author dzhu
 *
 * DAO for Reports
 */
public class HeronReportsDao extends HeronDBDao{
	/**
	 * get all users signed system access agreement
	 * @return a list of users
	 */
	public List getHeronSystemUsers(){
		String sql = "select user_id, user_full_name from heron.system_access_users";
		return this.getJdbcTemplate().queryForList(sql);
	}
	
	public List getApprovedUsers(String type){
		String sql = "select user_id, research_title,expire_date,kumc_empl_flag,kuh_approval_tmst,"+
			" kumc_approval_tmst,ukp_approval_tmst from HERON.sponsorship"+
			" where access_type ='" + type + "' and kumc_approval_status='A' and kuh_approval_status='A' "+
			" and ukp_approval_status='A' order by user_id";
		return this.getJdbcTemplate().queryForList(sql);
	}
}
