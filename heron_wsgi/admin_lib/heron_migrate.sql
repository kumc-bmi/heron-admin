create or replace view heron.oversight_request as
select
  min(sponsorship_id) as request_id
, signature as full_name -- replace from LDAP?
, sponsor_id as user_id
, req.research_title as project_title
, to_char(expire_date, 'yyyy-mm-dd hh:mm:ss') as date_of_expiration
, case access_type
  when 'VIEW_ONLY' then '1'
  when 'DATA_ACCESS' then '2'
  end as what_for
, case access_type
  when 'VIEW_ONLY' then research_desc
  when 'DATA_ACCESS' then null
  end as description_sponsor
, case access_type
  when 'VIEW_ONLY' then null
  when 'DATA_ACCESS' then research_desc
  end as data_use_description
, case
  when req.kumc_approval_status = 'A' then '1'
  when req.kumc_approval_status = 'N' then '2' -- not sure
  when req.kumc_approval_status = 'D' then '3'
  end as approve_kumc
, case
  when req.kuh_approval_status = 'A' then '1'
  when req.kuh_approval_status = 'N' then '2' -- not sure
  when req.kuh_approval_status = 'D' then '3'
  end as approve_kuh
, case
  when req.ukp_approval_status = 'A' then '1'
  when req.ukp_approval_status = 'N' then '2' -- not sure
  when req.ukp_approval_status = 'D' then '3'
  end as approve_ukp
, 'reviewed by ' || kumc_approved_by
  || ' at ' || to_char(kumc_approval_tmst, 'yyyy-mm-dd hh:mm:ss') as notes_kumc
, 'reviewed by ' || kuh_approved_by
  || ' at ' || to_char(kuh_approval_tmst, 'yyyy-mm-dd hh:mm:ss') as notes_kuh
, 'reviewed by ' || ukp_approved_by
  || ' at ' || to_char(ukp_approval_tmst, 'yyyy-mm-dd hh:mm:ss') as notes_ukp
from heron.sponsorship req
group by sponsor_id, research_title, signature, expire_date, access_type
       , research_desc
       , kumc_approval_status, kuh_approval_status, ukp_approval_status
       , kumc_approved_by, kuh_approved_by, ukp_approved_by
       , kumc_approval_tmst, kuh_approval_tmst, ukp_approval_tmst
order by min(sponsorship_id)
;

-- select * from heron_oversight_request;

create or replace view heron.sponsorship_candidates as
(select req.request_id, req.sponsor_id
, hs.sponsorship_id
, trim(hs.user_id) as user_id
, case hs.kumc_empl_flag
  when 'Y' then 1
  when 'N' then 2
  end as kumc_employee
, case hs.kumc_empl_flag
  when 'Y' then null
  when 'N' then hs.user_desc
  end as affiliation
from
(select
  min(sponsorship_id) as request_id, signed_date, sponsor_id, research_title
  from heron.sponsorship
  group by sponsor_id, research_title, signed_date) req
 join heron.sponsorship hs
  on req.sponsor_id=hs.sponsor_id and req.research_title=hs.research_title
)
order by hs.sponsorship_id
;

create or replace view system_access as
select user_id
     , user_full_name as full_name
     , signed_date
from heron.system_access_users sau;
