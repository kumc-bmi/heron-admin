package edu.kumc.informatics.heron.dao;

import java.sql.Types;

import javax.sql.DataSource;
import org.springframework.jdbc.core.SqlParameter;
import org.springframework.jdbc.object.BatchSqlUpdate;
/**
 * for sponsorship batch approval
 * 
 * @author dzhu
 *
 */
public class SponsorshipApprovalBatchUpdate extends BatchSqlUpdate {
	  public SponsorshipApprovalBatchUpdate(DataSource dataSource, String SQL) {
	    super(dataSource, SQL);
	    declareParameter(new SqlParameter(Types.VARCHAR));
	    declareParameter(new SqlParameter(Types.VARCHAR));
	    declareParameter(new SqlParameter(Types.NUMERIC));
	  }
}
