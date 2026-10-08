-- Orquestra Dev v1.0: durable worker leases, bounded retries and auditable stages.
-- Run on a NEW project dedicated to Orquestra, after 001_init and 002_integrations.
begin;

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

-- IMPORTANT: these RPCs are private (only server/service_role can invoke).
-- No user-provided shell command, path or credentials enter these functions.
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

-- User-submitted jobs are constrained to safe scheduling fields; never trust browser status.
drop policy if exists orq_tasks_add on public.orq_tasks;
create policy orq_tasks_add on public.orq_tasks for insert to authenticated
 with check (owner_id = (select auth.uid())
   and status='queued' and attempts=0 and node_id is null and started_at is null
   and finished_at is null and output is null and lease_expires_at is null
   and heartbeat_at is null and max_attempts=3 and priority=0);

commit;
