PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE notice_log (
	id INTEGER NOT NULL, 
	record VARCHAR(100), 
	timestamp TIMESTAMP, 
	PRIMARY KEY (id), 
	FOREIGN KEY(record) REFERENCES redcap_data (record)
);
INSERT INTO "notice_log" VALUES(1,'93180811818667777','2011-08-26 00:00:00.000000');
CREATE TABLE redcap_data (
	project_id INTEGER NOT NULL, 
	event_id INTEGER NOT NULL, 
	record VARCHAR(100) NOT NULL, 
	field_name VARCHAR(100) NOT NULL, 
	value TEXT, 
	PRIMARY KEY (project_id, event_id, record, field_name)
);
INSERT INTO "redcap_data" VALUES(123,1,'1','disclaimer_id','1');
INSERT INTO "redcap_data" VALUES(123,1,'1','url','http://example/blog/item/heron-release-xyz');
INSERT INTO "redcap_data" VALUES(123,1,'1','current','1');
INSERT INTO "redcap_data" VALUES(34,1,'6373469799195807417','user_id','john.smith');
INSERT INTO "redcap_data" VALUES(34,1,'6373469799195807417','full_name','John Smith');
INSERT INTO "redcap_data" VALUES(34,1,'6373469799195807417','project_title','Cure Warts');
INSERT INTO "redcap_data" VALUES(34,1,'6373469799195807417','what_for','1');
INSERT INTO "redcap_data" VALUES(34,1,'6373469799195807417','hsc_number','HSC123');
INSERT INTO "redcap_data" VALUES(34,1,'6373469799195807417','date_of_expiration','');
INSERT INTO "redcap_data" VALUES(34,1,'6373469799195807417','user_id_1','some.one');
INSERT INTO "redcap_data" VALUES(34,1,'6373469799195807417','team_email_1','some.one@example');
INSERT INTO "redcap_data" VALUES(34,1,'6373469799195807417','name_etc_1','Some One');
INSERT INTO "redcap_data" VALUES(34,1,'6373469799195807417','user_id_2','carol.student');
INSERT INTO "redcap_data" VALUES(34,1,'6373469799195807417','team_email_2','carol.student@example');
INSERT INTO "redcap_data" VALUES(34,1,'6373469799195807417','user_id_3','koam.rin');
INSERT INTO "redcap_data" VALUES(34,1,'6373469799195807417','approve_kuh','1');
INSERT INTO "redcap_data" VALUES(34,1,'6373469799195807417','approve_kupi','1');
INSERT INTO "redcap_data" VALUES(34,1,'6373469799195807417','approve_kumc','1');
INSERT INTO "redcap_data" VALUES(34,1,'3020449030017110101','user_id','john.smith');
INSERT INTO "redcap_data" VALUES(34,1,'3020449030017110101','full_name','John Smith');
INSERT INTO "redcap_data" VALUES(34,1,'3020449030017110101','project_title','Cure Hair Loss');
INSERT INTO "redcap_data" VALUES(34,1,'3020449030017110101','date_of_expiration','');
INSERT INTO "redcap_data" VALUES(34,1,'3020449030017110101','user_id_1','bill.student');
INSERT INTO "redcap_data" VALUES(34,1,'3020449030017110101','approve_kuh','1');
INSERT INTO "redcap_data" VALUES(34,1,'3020449030017110101','approve_kupi','1');
INSERT INTO "redcap_data" VALUES(34,1,'-565402122873664774','user_id','john.smith');
INSERT INTO "redcap_data" VALUES(34,1,'-565402122873664774','full_name','John Smith');
INSERT INTO "redcap_data" VALUES(34,1,'-565402122873664774','project_title','Cart Blanche');
INSERT INTO "redcap_data" VALUES(34,1,'-565402122873664774','date_of_expiration','');
INSERT INTO "redcap_data" VALUES(34,1,'-565402122873664774','user_id_1','bill.student');
INSERT INTO "redcap_data" VALUES(34,1,'-565402122873664774','approve_kuh','2');
INSERT INTO "redcap_data" VALUES(34,1,'-565402122873664774','approve_kupi','2');
INSERT INTO "redcap_data" VALUES(34,1,'-565402122873664774','approve_kumc','2');
INSERT INTO "redcap_data" VALUES(34,1,'23180811818680005','user_id','john.smith');
INSERT INTO "redcap_data" VALUES(34,1,'23180811818680005','full_name','John Smith');
INSERT INTO "redcap_data" VALUES(34,1,'23180811818680005','project_title','Cure Polio');
INSERT INTO "redcap_data" VALUES(34,1,'23180811818680005','date_of_expiration','1950-02-27');
INSERT INTO "redcap_data" VALUES(34,1,'23180811818680005','user_id_1','bill.student');
INSERT INTO "redcap_data" VALUES(34,1,'23180811818680005','approve_kuh','1');
INSERT INTO "redcap_data" VALUES(34,1,'23180811818680005','approve_kupi','1');
INSERT INTO "redcap_data" VALUES(34,1,'23180811818680005','approve_kumc','1');
INSERT INTO "redcap_data" VALUES(34,1,'93180811818667777','user_id','prof.fickle');
INSERT INTO "redcap_data" VALUES(34,1,'93180811818667777','full_name','Prof Fickle');
INSERT INTO "redcap_data" VALUES(34,1,'93180811818667777','project_title','Change how diabetes is treated');
INSERT INTO "redcap_data" VALUES(34,1,'93180811818667777','what_for','1');
INSERT INTO "redcap_data" VALUES(34,1,'93180811818667777','date_of_expiration','2050-02-27');
INSERT INTO "redcap_data" VALUES(34,1,'93180811818667777','user_id_1','jill.student');
INSERT INTO "redcap_data" VALUES(34,1,'93180811818667777','approve_kuh','1');
INSERT INTO "redcap_data" VALUES(34,1,'93180811818667777','approve_kupi','1');
INSERT INTO "redcap_data" VALUES(34,1,'93180811818667777','approve_kumc','1');
-- missing user_id
INSERT INTO "redcap_data" VALUES(34,1,'3180811818667777','full_name','Prof Fickle');
INSERT INTO "redcap_data" VALUES(34,1,'3180811818667777','project_title','goofy: Change how diabetes is treated');
INSERT INTO "redcap_data" VALUES(34,1,'3180811818667777','date_of_expiration','2050-02-27');
INSERT INTO "redcap_data" VALUES(34,1,'3180811818667777','user_id_1','jill.student');
INSERT INTO "redcap_data" VALUES(34,1,'3180811818667777','approve_kuh','1');
INSERT INTO "redcap_data" VALUES(34,1,'3180811818667777','approve_kupi','1');
INSERT INTO "redcap_data" VALUES(34,1,'3180811818667777','approve_kumc','1');
CREATE TABLE redcap_surveys_participants (
	participant_id INTEGER NOT NULL, 
	survey_id INTEGER, 
	event_id INTEGER, 
	hash VARCHAR(6), 
	legacy_hash VARCHAR(32), 
	participant_email VARCHAR(255), 
	participant_identifier VARCHAR(255), 
	PRIMARY KEY (participant_id)
);
INSERT INTO "redcap_surveys_participants" VALUES(1956,11,1,'hash1',NULL,'trouble.maker@js.example',NULL);
INSERT INTO "redcap_surveys_participants" VALUES(3253004250825796194,11,1,NULL,NULL,'big.wig@js.example',NULL);
INSERT INTO "redcap_surveys_participants" VALUES(7868139340274461544,11,1,NULL,NULL,'john.smith@js.example',NULL);
INSERT INTO "redcap_surveys_participants" VALUES(7868139340274461590,11,1,NULL,NULL,'prof.fickle@js.example',NULL);
CREATE TABLE redcap_surveys_response (
	response_id INTEGER NOT NULL, 
	participant_id INTEGER, 
	record VARCHAR(100), 
	first_submit_time DATETIME_CHAR, 
	completion_time DATETIME_CHAR, 
	return_code VARCHAR(8), 
	PRIMARY KEY (response_id)
);
INSERT INTO "redcap_surveys_response" VALUES(6591,1956,'19560',NULL,'2015-11-16 21:41:01',NULL);
INSERT INTO "redcap_surveys_response" VALUES(3253004250825796194,3253004250825796194,'3253004250825796194',NULL,'2011-08-26 00:00:00.000000',NULL);
INSERT INTO "redcap_surveys_response" VALUES(7868139340274461544,7868139340274461544,'7868139340274461544',NULL,'2011-08-26 00:00:00.000000',NULL);
INSERT INTO "redcap_surveys_response" VALUES(7868139340274461590,7868139340274461590,'7868139340274461590',NULL,'2011-08-26 00:00:00.000000',NULL);
CREATE TABLE redcap_user_rights (
	project_id INTEGER, 
	username VARCHAR
);
INSERT INTO "redcap_user_rights" VALUES(34,'big.wig');

CREATE TABLE redcap_surveys (
       survey_id INTEGER NOT NULL, 
       project_id INTEGER, 
       PRIMARY KEY (survey_id)
);
INSERT INTO redcap_surveys (survey_id, project_id) VALUES (11, 2377);

CREATE TABLE redcap_events_arms (
       arm_id INTEGER NOT NULL, 
       project_id INTEGER, 
       PRIMARY KEY (arm_id)
);
INSERT INTO redcap_events_arms (arm_id, project_id) VALUES (843, 2377);

CREATE TABLE redcap_events_metadata (
       event_id INTEGER NOT NULL, 
       arm_id INTEGER, 
       PRIMARY KEY (event_id)
);
INSERT INTO redcap_events_metadata (event_id, arm_id) VALUES (1, 843);
COMMIT;
