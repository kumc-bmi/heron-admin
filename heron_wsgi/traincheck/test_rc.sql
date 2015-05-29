CREATE TABLE redcap_data (
	project_id INTEGER NOT NULL, 
	event_id INTEGER NOT NULL, 
	record VARCHAR(100) NOT NULL, 
	field_name VARCHAR(100) NOT NULL, 
	value TEXT, 
	PRIMARY KEY (project_id, event_id, record, field_name)
);
