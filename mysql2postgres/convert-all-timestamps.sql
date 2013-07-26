
-- SELEct 'alter table '||table_name||' alter '||column_name||' type timestamp with time zone;'
-- from information_schema.columns
-- where data_type = 'timestamp without time zone';

 alter table main_eventtweet alter send_date type timestamp with time zone;
 alter table main_eventtweet alter sent_date type timestamp with time zone;
 alter table auth_user alter last_login type timestamp with time zone;
 alter table auth_user alter date_joined type timestamp with time zone;
 alter table django_session alter expire_date type timestamp with time zone;
 alter table djcelery_periodictask alter expires type timestamp with time zone;
 alter table djcelery_periodictask alter last_run_at type timestamp with time zone;
 alter table djcelery_periodictask alter date_changed type timestamp with time zone;
 alter table djcelery_periodictasks alter last_update type timestamp with time zone;
 alter table djcelery_taskstate alter tstamp type timestamp with time zone;
 alter table djcelery_taskstate alter eta type timestamp with time zone;
 alter table djcelery_taskstate alter expires type timestamp with time zone;
 alter table djcelery_workerstate alter last_heartbeat type timestamp with time zone;
 alter table main_approval alter processed_time type timestamp with time zone;
 alter table main_channel alter created type timestamp with time zone;
 alter table main_event alter start_time type timestamp with time zone;
 alter table main_event alter archive_time type timestamp with time zone;
 alter table main_event alter created type timestamp with time zone;
 alter table main_event alter modified type timestamp with time zone;
 alter table main_eventhitstats alter modified type timestamp with time zone;
 alter table main_suggestedevent alter start_time type timestamp with time zone;
 alter table main_suggestedevent alter created type timestamp with time zone;
 alter table main_suggestedevent alter modified type timestamp with time zone;
 alter table main_suggestedevent alter submitted type timestamp with time zone;
 alter table main_suggestedeventcomment alter created type timestamp with time zone;
 alter table main_urlmatch alter modified type timestamp with time zone;
 alter table main_vidlysubmission alter submission_time type timestamp with time zone;
 alter table south_migrationhistory alter applied type timestamp with time zone;
