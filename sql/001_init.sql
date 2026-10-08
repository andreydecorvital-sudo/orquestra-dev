-- Orquestra Dev Lite / schema separado de qualquer sistema existente.
create extension if not exists pgcrypto;

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

-- Remover grants herdados em schemas public antigos. O navegador nunca altera estados de execução.
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

-- Só backend confiável chama a função. SELECT FOR UPDATE SKIP LOCKED evita dupla execução.
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

-- SQL opcional para recuperar tarefa interrompida, somente via console administrativo:
-- update public.orq_tasks set status='queued',node_id=null,started_at=null
-- where id='<ID>' and status='running';
