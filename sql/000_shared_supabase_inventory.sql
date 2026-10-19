-- READ ONLY inventory for the Supabase project Chatbot.
-- Run only after checking the project reference in Dashboard > Project Settings.
-- This file does not create, alter, insert, delete, or grant anything.
-- A nonzero existing_orq_* count requires human review before running 001-005.
with rels as (
  select c.relname
  from pg_catalog.pg_class c
  join pg_catalog.pg_namespace n on n.oid = c.relnamespace
  where n.nspname = 'public'
    and c.relname like 'orq\_%' escape '\'
    and c.relkind in ('r','p','v','m','f')
),
routines as (
  select p.proname
  from pg_catalog.pg_proc p
  join pg_catalog.pg_namespace n on n.oid = p.pronamespace
  where n.nspname = 'public'
    and p.proname like 'orq\_%' escape '\'
),
policies as (
  select policyname
  from pg_catalog.pg_policies
  where schemaname = 'public'
    and policyname like 'orq\_%' escape '\'
),
checks as (
  select
    (select count(*) from rels) as existing_orq_relations,
    (select count(*) from routines) as existing_orq_routines,
    (select count(*) from policies) as existing_orq_policies,
    pg_catalog.to_regclass('auth.users') is not null as auth_users_available,
    exists(select 1 from pg_catalog.pg_extension where extname='pgcrypto') as pgcrypto_present
)
select
  existing_orq_relations,
  existing_orq_routines,
  existing_orq_policies,
  auth_users_available,
  pgcrypto_present,
  case
    when not auth_users_available then 'BLOCKED_AUTH_MISSING'
    when existing_orq_relations > 0 or existing_orq_routines > 0 or existing_orq_policies > 0
      then 'REVIEW_EXISTING_ORQ_OBJECTS'
    else 'NO_ORQ_OBJECT_COLLISIONS'
  end as inventory_result
from checks;
