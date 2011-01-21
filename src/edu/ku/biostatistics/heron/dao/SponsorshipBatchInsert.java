package edu.ku.biostatistics.heron.dao;

import java.sql.Types;

import javax.sql.DataSource;

import org.springframework.jdbc.core.SqlParameter;
import org.springframework.jdbc.object.BatchSqlUpdate;
/**
 * for batch insert of sponsorship
 * 
 * @author dzhu
 *
 */
public class SponsorshipBatchInsert  extends BatchSqlUpdate {
	  private static final String SQL = "insert into heron.SPONSORSHIP(UNIQ_ID,USER_ID,SPONSOR_ID,LAST_UPDT_TMST,"+
	  	"ACCESS_TYPE,RESEARCH_TITLE,RESEARCH_DESC,EXPIRE_DATE,KUMC_EMPL_FLAG,SIGNATURE,SIGNED_DATE) "+
	  	"values (heron.seq_sponsorship.nextval,?, ?, sysdate, ?, ?,?,?,?,?,?)";

	  SponsorshipBatchInsert(DataSource dataSource) {
	    super(dataSource, SQL);
	    declareParameter(new SqlParameter(Types.VARCHAR));
	    declareParameter(new SqlParameter(Types.VARCHAR));
	    declareParameter(new SqlParameter(Types.VARCHAR));
	    declareParameter(new SqlParameter(Types.VARCHAR));
	    declareParameter(new SqlParameter(Types.VARCHAR));
	    declareParameter(new SqlParameter(Types.DATE));
	    declareParameter(new SqlParameter(Types.VARCHAR));
	    declareParameter(new SqlParameter(Types.VARCHAR));
	    declareParameter(new SqlParameter(Types.DATE));
	    setBatchSize(100);
	}
}
