-- READ ONLY. Run ONLY AFTER an authorized migration to the Chatbot project.
-- This is not a tenant isolation test: still test as two distinct authenticated users.
-- No PII, secrets, or data rows are queried.

with orq_tables as (
  select c.relname as object_name,
         c.relrowsecurity as rls_enabled,
         pg_catalog.has_table_privilege('anon', c.oid, 'SELECT') as anon_can_select,
         pg_catalog.has_table_privilege('authenticated', c.oid, 'INSERT') as authenticated_can_insert
    from pg_catalog.pg_class c
    join pg_catalog.pg_namespace n on n.oid=c.relnamespace
   where n.nspname='public' and c.relname in
     ('orq_projects','orq_nodes','orq_tasks','orq_task_events')
),
secret as (
  select case
    when pg_catalog.to_regclass('public.orq_nodes') is not null then
      pg_catalog.has_column_privilege(
        'authenticated','public.orq_nodes','secret_hash','SELECT'
      )
    else true
  end as device_secret_readable_to_authenticated
),
rpcs as (
  select
    count(*) as rpc_count,
    coalesce(bool_or(pg_catalog.has_function_privilege(
      'anon', p.oid,'EXECUTE'
    )),false) as any_rpc_callable_by_anon,
    coalesce(bool_or(pg_catalog.has_function_privilege(
      'authenticated',p.oid,'EXECUTE'
    )),false) as any_rpc_callable_by_authenticated,
    coalesce(bool_and(p.prosecdef),false) as all_rpc_security_definer
  from pg_catalog.pg_proc p
  join pg_catalog.pg_namespace n on n.oid=p.pronamespace
  where n.nspname='public' and p.proname in
    ('orq_claim_task','orq_heartbeat_task','orq_finish_task')
)
select
  (select count(*) from orq_tables) as orq_table_count,
  (select coalesce(bool_and(rls_enabled),false) from orq_tables) as all_orq_rls_enabled,
  (select coalesce(bool_or(anon_can_select),false) from orq_tables) as any_orq_table_readable_by_anon,
  (select device_secret_readable_to_authenticated from secret) as device_secret_exposed,
  (select rpc_count from rpcs) as rpc_count,
  (select any_rpc_callable_by_anon from rpcs) as rpc_public_to_anon,
  (select any_rpc_callable_by_authenticated from rpcs) as rpc_public_to_authenticated,
  (select all_rpc_security_definer from rpcs) as rpc_security_definer,
  case
    when (select count(*) from orq_tables) != 4 then 'BLOCKED_TABLES_MISSING'
    when (select coalesce(bool_and(rls_enabled),false) from orq_tables) is not true then 'BLOCKED_RLS'
    when (select coalesce(bool_or(anon_can_select),false) from orq_tables) then 'BLOCKED_ANON_PRIVILEGES'
    when (select device_secret_readable_to_authenticated from secret) then 'BLOCKED_SECRET_EXPOSURE'
    when (select rpc_count from rpcs) != 3 then 'BLOCKED_RPC_COUNT'
    when (select any_rpc_callable_by_anon from rpcs)
      or (select any_rpc_callable_by_authenticated from rpcs) then 'BLOCKED_RPC_PUBLIC'
    when (select all_rpc_security_definer from rpcs) is not true then 'BLOCKED_RPC_SECURITY_MODE'
    else 'STATIC_SECURITY_CHECKS_PASS'
  end as postcheck_result;
