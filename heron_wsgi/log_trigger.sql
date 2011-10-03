delimiter //

/*
SELECT current_timestamp
          INTO OUTFILE 
                   '/tmp/heron_notices/oversight';
*/

DROP PROCEDURE if exists redcap.log_per_project
//

CREATE PROCEDURE redcap.log_per_project(IN actual INT, IN record INT, IN expected INT)
BEGIN
    IF actual = expected THEN
      SELECT current_timestamp, actual, record
          INTO OUTFILE 
                   '/tmp/heron_notices/oversight';
    END IF;
END
//

DROP TRIGGER if exists redcap.notifylog
//
CREATE TRIGGER redcap.notifylog AFTER INSERT ON redcap.redcap_data
FOR EACH ROW CALL log_per_project(new.project_id, new.record, 34);
//

DROP TRIGGER if exists redcap.notifylog
//
CREATE TRIGGER redcap.notifylog AFTER UPDATE ON redcap.redcap_data
FOR EACH ROW CALL log_per_project(new.project_id, new.record, 34);
//
