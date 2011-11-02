select
  min(sponsorship_id) as record
, 'project_title' as field_name
, req.research_title as value
from heron.sponsorship req
group by sponsor_id, research_title

union all

select
  min(sponsorship_id) as record
, 'user_id' as field_name
, req.sponsor_id as value
from heron.sponsorship req
group by sponsor_id, research_title

union all

select
  min(sponsorship_id) as record
, 'what_for' as field_name
, case req.access_type
  when 'VIEW_ONLY' then '1'
  when 'DATA_ACCESS' then '2'
  end as value
from heron.sponsorship req
group by sponsor_id, research_title, access_type

union all

select
  min(sponsorship_id) as record
, 'approve_kumc' as field_name
, case
  when req.kumc_approval_status = 'A' then '1'
  when req.kumc_approval_status = 'N' then '2' -- not sure
  when req.kumc_approval_status = 'D' then '3'
  end as value
from heron.sponsorship req
where req.kumc_approval_status is not null
group by sponsor_id, research_title, kumc_approval_status

union all

select
  min(sponsorship_id) as record
, 'approve_ukp' as field_name
, case
  when req.ukp_approval_status = 'A' then '1'
  when req.ukp_approval_status = 'N' then '2' -- not sure
  when req.ukp_approval_status = 'D' then '3'
  end as value
from heron.sponsorship req
where req.ukp_approval_status is not null
group by sponsor_id, research_title, ukp_approval_status

union all

select
  min(sponsorship_id) as record
, 'approve_kuh' as field_name
, case
  when req.kuh_approval_status = 'A' then '1'
  when req.kuh_approval_status = 'N' then '2' -- not sure
  when req.kuh_approval_status = 'D' then '3'
  end as value
from heron.sponsorship req
where req.kuh_approval_status is not null
group by sponsor_id, research_title, kuh_approval_status

-- repeat for kuh, ukp

union all

(select req.record
, 'user_id_' || hs.sponsorship_id as field_name
, trim(hs.user_id) as value
from
(select
  min(sponsorship_id) as record, sponsor_id, research_title
  from heron.sponsorship
  group by sponsor_id, research_title) req
 join heron.sponsorship hs
  on req.sponsor_id=hs.sponsor_id and req.research_title=hs.research_title
)

order by 1, 2
;

select sponsorship_id, user_id, req.sponsor_id, req.research_title
from (
select distinct sponsor_id, research_title
from heron.sponsorship) req
join heron.sponsorship hs
 on hs.sponsor_id = req.sponsor_id
 and hs.research_title = req.research_title
;

select distinct kumc_approval_status, ukp_approval_status, kuh_approval_status, req.sponsor_id, req.research_title
from (
select distinct sponsor_id, research_title
from heron.sponsorship) req
join heron.sponsorship hs
 on hs.sponsor_id = req.sponsor_id
 and hs.research_title = req.research_title
;

select *
from heron.sponsorship;
