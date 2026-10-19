-- Supabase Chatbot (ydyzjpcmavqffdazteib): PROPOSED, NOT EXECUTED.
-- CRM IS ACTIVE IN THIS PROJECT. Run ONLY after explicit database-write authorization,
-- off-peak/recovery planning, and verifying the destination in Supabase Studio.
--
-- This migration uses ONLY names public.orq_* and existing auth.users IDs.
-- It DOES NOT alter CRM tables, existing users, existing Auth configuration,
-- project-wide grants, schema-level permissions or other Edge Functions.
-- Atomic: any failed check/statement rolls back all Orquestra DDL.
-- NOT idempotent: it refuses to run if ANY orq_* object already exists.
-- service_role is a PROJECT-WIDE trust boundary: physical tenant isolation is NOT promised.

BEGIN;

DO $orq_preflight$
DECLARE
  v_project_name text;
BEGIN
  IF pg_catalog.to_regclass('auth.users') IS NULL THEN
    RAISE EXCEPTION 'BLOCKED: auth.users unavailable';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_extension WHERE extname='pgcrypto') THEN
    RAISE EXCEPTION 'BLOCKED: pgcrypto missing - do not install extensions automatically on shared CRM';
  END IF;
  IF EXISTS (
    SELECT 1 FROM pg_catalog.pg_class c
      JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
     WHERE n.nspname='public' AND c.relname LIKE 'orq\_%' ESCAPE '\'
  ) OR EXISTS (
    SELECT 1 FROM pg_catalog.pg_proc p
      JOIN pg_catalog.pg_namespace n ON n.oid=p.pronamespace
     WHERE n.nspname='public' AND p.proname LIKE 'orq\_%' ESCAPE '\'
  ) OR EXISTS (
    SELECT 1 FROM pg_catalog.pg_policies
     WHERE schemaname='public' AND policyname LIKE 'orq\_%' ESCAPE '\'
  ) THEN
    RAISE EXCEPTION 'BLOCKED: existing orq_ objects. Audit before reapplying.';
  END IF;
END;
$orq_preflight$;

-- Source: sql/001_init.sql, folded atomically after collision gate
create table if not exists public.orq_projects (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  name text not null check (char_length(name) between 2 and 90),
  repo_url text not null default '',
  created_at timestamptz not null default now(),
  unique (id, owner_id)
);

create table if not exists public.orq_nodes (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  name text not null check (char_length(name) between 1 and 90),
  secret_hash text not null,
  last_seen_at timestamptz,
  revoked_at timestamptz,
  created_at timestamptz not null default now(),
  unique (id, owner_id)
);

create table if not exists public.orq_tasks (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  project_id uuid not null,
  preferred_node_id uuid,
  node_id uuid,
  kind text not null check (kind in ('diagnose','codex','integrations')),
  title text not null check (char_length(title) between 3 and 140),
  instructions text not null check (char_length(instructions) between 5 and 12000),
  status text not null default 'queued' check (status in ('queued','running','completed','failed','cancelled')),
  attempts integer not null default 0 check(attempts >= 0),
  created_at timestamptz not null default now(),
  started_at timestamptz,
  finished_at timestamptz,
  output text,
  constraint orq_task_owner_project foreign key(project_id, owner_id) references public.orq_projects(id, owner_id) on delete cascade,
  constraint orq_task_preferred_node foreign key(preferred_node_id, owner_id) references public.orq_nodes(id, owner_id),
  constraint orq_task_node foreign key(node_id, owner_id) references public.orq_nodes(id, owner_id)
);

create index if not exists orq_tasks_queue_idx on public.orq_tasks(owner_id, created_at) where status = 'queued';
create index if not exists orq_tasks_recent_idx on public.orq_tasks(owner_id, created_at desc);

alter table public.orq_projects enable row level security;
alter table public.orq_nodes enable row level security;
alter table public.orq_tasks enable row level security;

revoke all on public.orq_projects, public.orq_nodes, public.orq_tasks from anon, authenticated;
grant select, insert on public.orq_projects to authenticated;
grant select on public.orq_nodes to authenticated;
grant select, insert on public.orq_tasks to authenticated;

create policy orq_projects_read on public.orq_projects for select to authenticated using (owner_id = (select auth.uid()));
create policy orq_projects_add on public.orq_projects for insert to authenticated with check (owner_id = (select auth.uid()));
create policy orq_nodes_read on public.orq_nodes for select to authenticated using (owner_id = (select auth.uid()));
create policy orq_tasks_read on public.orq_tasks for select to authenticated using (owner_id = (select auth.uid()));
create policy orq_tasks_add on public.orq_tasks for insert to authenticated
 with check (owner_id = (select auth.uid()) and status = 'queued' and attempts = 0 and node_id is null and started_at is null and finished_at is null and output is null);

create or replace function public.orq_claim_task(p_node_id uuid)
returns setof public.orq_tasks
language plpgsql security definer set search_path = '' as $$
declare
  v_owner uuid;
begin
  select owner_id into v_owner from public.orq_nodes where id = p_node_id and revoked_at is null;
  if v_owner is null then return; end if;
  return query
  update public.orq_tasks t
     set status='running', node_id=p_node_id, started_at=now(), attempts=t.attempts+1
   where t.id = (
     select q.id from public.orq_tasks q
      where q.owner_id = v_owner and q.status='queued'
        and (q.preferred_node_id is null or q.preferred_node_id=p_node_id)
      order by q.created_at asc for update skip locked limit 1
   )
   returning t.*;
end; $$;
revoke all on function public.orq_claim_task(uuid) from public, anon, authenticated;
grant execute on function public.orq_claim_task(uuid) to service_role;

-- Source: sql/002_integrations.sql, folded atomically after collision gate
alter table public.orq_tasks drop constraint if exists orq_tasks_kind_check;
alter table public.orq_tasks
  add constraint orq_tasks_kind_check
  check (kind in ('diagnose','codex','integrations'));

-- Source: sql/003_durable_execution.sql, folded atomically after collision gate
alter table public.orq_tasks
  add column if not exists lease_expires_at timestamptz,
  add column if not exists heartbeat_at timestamptz,
  add column if not exists next_attempt_at timestamptz not null default now(),
  add column if not exists max_attempts integer not null default 3,
  add column if not exists priority smallint not null default 0;

alter table public.orq_tasks drop constraint if exists orq_tasks_kind_check;
alter table public.orq_tasks add constraint orq_tasks_kind_check
  check (kind in ('diagnose','integrations','codex','claude','joint'));
alter table public.orq_tasks drop constraint if exists orq_tasks_max_attempts_check;
alter table public.orq_tasks add constraint orq_tasks_max_attempts_check
  check (max_attempts between 1 and 5);
alter table public.orq_tasks drop constraint if exists orq_tasks_priority_check;
alter table public.orq_tasks add constraint orq_tasks_priority_check
  check (priority between -5 and 5);

alter table public.orq_nodes
  add column if not exists capabilities text[] not null default array['diagnose','integrations']::text[];
alter table public.orq_nodes drop constraint if exists orq_nodes_capabilities_check;
alter table public.orq_nodes add constraint orq_nodes_capabilities_check
  check (capabilities <@ array['diagnose','integrations','codex','claude','joint']::text[]);

create index if not exists orq_tasks_lease_idx
  on public.orq_tasks (lease_expires_at)
  where status = 'running';
create index if not exists orq_tasks_retry_idx
  on public.orq_tasks (priority desc, next_attempt_at, created_at)
  where status = 'queued';

create table if not exists public.orq_task_events (
  id bigint generated always as identity primary key,
  owner_id uuid not null references auth.users(id) on delete cascade,
  task_id uuid not null references public.orq_tasks(id) on delete cascade,
  event_type text not null check (event_type in ('claimed','heartbeat','reclaimed','completed','failed')),
  node_id uuid references public.orq_nodes(id) on delete set null,
  details text not null default '' check (length(details) <= 1000),
  created_at timestamptz not null default now()
);
create index if not exists orq_events_task_idx
  on public.orq_task_events(owner_id, task_id, created_at desc);
alter table public.orq_task_events enable row level security;
revoke all on public.orq_task_events from public, anon, authenticated;
grant select on public.orq_task_events to authenticated;
create policy orq_events_read on public.orq_task_events for select to authenticated
 using (owner_id = (select auth.uid()));

create or replace function public.orq_claim_task(p_node_id uuid)
returns setof public.orq_tasks
language plpgsql security definer set search_path = '' as $$
declare
  v_owner uuid;
  v_capabilities text[];
  v_task public.orq_tasks%rowtype;
  v_previous text;
begin
  select n.owner_id,n.capabilities into v_owner,v_capabilities from public.orq_nodes n
    where n.id = p_node_id and n.revoked_at is null;
  if v_owner is null then return; end if;

  -- Terminal failure of abandoned jobs after their retry budget is exhausted.
  with expired as (
    update public.orq_tasks t set status='failed',
      finished_at=now(), output='Tempo limite de execução excedido; tentativas esgotadas',
      lease_expires_at=null
    where t.owner_id=v_owner and t.status='running' and t.lease_expires_at < now()
      and t.attempts >= t.max_attempts
    returning t.id,t.owner_id,t.node_id
  )
  insert into public.orq_task_events(owner_id,task_id,node_id,event_type,details)
  select owner_id,id,node_id,'failed','Limite de tentativas esgotado' from expired;

  select t.* into v_task
  from public.orq_tasks t
  where t.id = (
    select q.id from public.orq_tasks q
    where q.owner_id=v_owner
      and q.kind = any(v_capabilities)
      and (q.preferred_node_id is null or q.preferred_node_id=p_node_id)
      and (
        (q.status='queued' and q.next_attempt_at <= now()) or
        (q.status='running' and q.lease_expires_at < now() and q.attempts < q.max_attempts)
      )
    order by q.priority desc, q.created_at asc
    for update skip locked limit 1
  ) for update skip locked;
  if not found then return; end if;

  v_previous := v_task.status;
  update public.orq_tasks t set
      status='running', node_id=p_node_id, started_at=now(),
      heartbeat_at=now(), lease_expires_at=now()+interval '8 minutes',
      attempts=t.attempts+1, output=null
    where t.id=v_task.id returning t.* into v_task;
  insert into public.orq_task_events(owner_id,task_id,node_id,event_type,details)
    values (v_owner,v_task.id,p_node_id,
      case when v_previous='running' then 'reclaimed' else 'claimed' end,
      'Tentativa '||v_task.attempts::text||' de '||v_task.max_attempts::text);
  return next v_task;
end;
$$;
revoke all on function public.orq_claim_task(uuid) from public, anon, authenticated;
grant execute on function public.orq_claim_task(uuid) to service_role;

create or replace function public.orq_heartbeat_task(p_node_id uuid,p_task_id uuid)
returns boolean
language plpgsql security definer set search_path = '' as $$
declare v_task public.orq_tasks%rowtype;
begin
  update public.orq_tasks t set heartbeat_at=now(), lease_expires_at=now()+interval '8 minutes'
  where t.id=p_task_id and t.node_id=p_node_id and t.status='running'
    and t.lease_expires_at > now()
    and exists (select 1 from public.orq_nodes n where n.id=p_node_id
      and n.owner_id=t.owner_id and n.revoked_at is null)
  returning t.* into v_task;
  if not found then return false; end if;
  -- Heartbeat events can be sampled in application logs; avoid filling event table each poll.
  return true;
end;
$$;
revoke all on function public.orq_heartbeat_task(uuid,uuid) from public, anon, authenticated;
grant execute on function public.orq_heartbeat_task(uuid,uuid) to service_role;

create or replace function public.orq_finish_task(p_node_id uuid,p_task_id uuid,p_ok boolean,p_output text)
returns boolean
language plpgsql security definer set search_path = '' as $$
declare v_task public.orq_tasks%rowtype;
begin
  update public.orq_tasks t set
    status=case when p_ok then 'completed' else 'failed' end,
    output=left(coalesce(p_output,''),18000), finished_at=now(),lease_expires_at=null
  where t.id=p_task_id and t.node_id=p_node_id and t.status='running'
    and t.lease_expires_at > now()
    and exists (select 1 from public.orq_nodes n where n.id=p_node_id
      and n.owner_id=t.owner_id and n.revoked_at is null)
  returning t.* into v_task;
  if not found then return false; end if;
  insert into public.orq_task_events(owner_id,task_id,node_id,event_type,details)
    values(v_task.owner_id,v_task.id,p_node_id,
     case when p_ok then 'completed' else 'failed' end,'Relatório armazenado');
  return true;
end;
$$;
revoke all on function public.orq_finish_task(uuid,uuid,boolean,text) from public, anon, authenticated;
grant execute on function public.orq_finish_task(uuid,uuid,boolean,text) to service_role;

drop policy if exists orq_tasks_add on public.orq_tasks;
create policy orq_tasks_add on public.orq_tasks for insert to authenticated
 with check (owner_id = (select auth.uid())
   and status='queued' and attempts=0 and node_id is null and started_at is null
   and finished_at is null and output is null and lease_expires_at is null
   and heartbeat_at is null and max_attempts=3 and priority=0);

-- Source: sql/004_execution_fencing.sql, folded atomically after collision gate
revoke select on table public.orq_nodes from authenticated;
grant select(id,owner_id,name,last_seen_at,revoked_at,capabilities,created_at)
  on table public.orq_nodes to authenticated;

drop function if exists public.orq_heartbeat_task(uuid,uuid);
drop function if exists public.orq_finish_task(uuid,uuid,boolean,text);

create function public.orq_heartbeat_task(p_node_id uuid,p_task_id uuid,p_attempt integer)
returns boolean
language plpgsql security definer set search_path = '' as $$
begin
  update public.orq_tasks t
     set heartbeat_at=now(), lease_expires_at=now()+interval '8 minutes'
   where t.id=p_task_id and t.node_id=p_node_id and t.status='running'
     and t.attempts=p_attempt and p_attempt between 1 and 5
     and t.lease_expires_at > now()
     and exists (
       select 1 from public.orq_nodes n
        where n.id=p_node_id and n.owner_id=t.owner_id and n.revoked_at is null
     );
  return found;
end; $$;
revoke all on function public.orq_heartbeat_task(uuid,uuid,integer) from public,anon,authenticated;
grant execute on function public.orq_heartbeat_task(uuid,uuid,integer) to service_role;

create function public.orq_finish_task(p_node_id uuid,p_task_id uuid,p_attempt integer,p_ok boolean,p_output text)
returns boolean
language plpgsql security definer set search_path = '' as $$
declare v_task public.orq_tasks%rowtype;
begin
  update public.orq_tasks t
     set status=case when p_ok then 'completed' else 'failed' end,
         output=left(coalesce(p_output,''),18000),
         finished_at=now(),lease_expires_at=null
   where t.id=p_task_id and t.node_id=p_node_id and t.status='running'
     and t.attempts=p_attempt and p_attempt between 1 and 5
     and t.lease_expires_at > now()
     and exists (
       select 1 from public.orq_nodes n
        where n.id=p_node_id and n.owner_id=t.owner_id and n.revoked_at is null
     )
  returning t.* into v_task;
  if not found then return false; end if;
  insert into public.orq_task_events(owner_id,task_id,node_id,event_type,details)
    values(v_task.owner_id,v_task.id,p_node_id,
      case when p_ok then 'completed' else 'failed' end,
      'Tentativa '||p_attempt::text||' finalizada');
  return true;
end; $$;
revoke all on function public.orq_finish_task(uuid,uuid,integer,boolean,text) from public,anon,authenticated;
grant execute on function public.orq_finish_task(uuid,uuid,integer,boolean,text) to service_role;

create index if not exists orq_nodes_owner_idx on public.orq_nodes(owner_id);
create index if not exists orq_projects_owner_idx on public.orq_projects(owner_id);
create index if not exists orq_task_events_node_idx on public.orq_task_events(node_id);
create index if not exists orq_task_events_task_idx on public.orq_task_events(task_id);
create index if not exists orq_tasks_node_owner_idx on public.orq_tasks(node_id,owner_id);
create index if not exists orq_tasks_project_owner_idx on public.orq_tasks(project_id,owner_id);
create index if not exists orq_tasks_preferred_owner_idx on public.orq_tasks(preferred_node_id,owner_id);

-- Source: sql/005_hermes_kind.sql, folded atomically after collision gate
alter table public.orq_tasks drop constraint if exists orq_tasks_kind_check;
alter table public.orq_tasks add constraint orq_tasks_kind_check
  check (kind in ('diagnose','integrations','codex','claude','joint','hermes'));
alter table public.orq_nodes drop constraint if exists orq_nodes_capabilities_check;
alter table public.orq_nodes add constraint orq_nodes_capabilities_check
  check (capabilities <@ array['diagnose','integrations','codex','claude','joint','hermes']::text[]);

-- Newly-created Orquestra objects require server-side service_role access;
-- no global/default grants are changed, and Auth users remain shared.
GRANT ALL ON TABLE public.orq_projects, public.orq_nodes, public.orq_tasks,
  public.orq_task_events TO service_role;
GRANT USAGE, SELECT ON SEQUENCE public.orq_task_events_id_seq TO service_role;

COMMIT;

-- POST-CHECK (read-only, separately):
-- select relname, relrowsecurity from pg_class where relname like 'orq\_%' escape '\';
-- Never deploy orq-worker until RLS and Edge Function checks pass.
