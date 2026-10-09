-- Orquestra: attempt-fenced leases; prevent old workers completing a reclaimed task.
-- Also remove client SELECT access to stored device secret hashes.
begin;

revoke select on table public.orq_nodes from authenticated;
grant select(id,owner_id,name,last_seen_at,revoked_at,capabilities,created_at)
  on table public.orq_nodes to authenticated;

-- Remove the obsolete unfenced RPC signatures so service callers cannot bypass
-- the attempt guard by calling the old overload.
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

-- Cover foreign-key lookups frequently used during deletes and RLS joins.
create index if not exists orq_nodes_owner_idx on public.orq_nodes(owner_id);
create index if not exists orq_projects_owner_idx on public.orq_projects(owner_id);
create index if not exists orq_task_events_node_idx on public.orq_task_events(node_id);
create index if not exists orq_task_events_task_idx on public.orq_task_events(task_id);
create index if not exists orq_tasks_node_owner_idx on public.orq_tasks(node_id,owner_id);
create index if not exists orq_tasks_project_owner_idx on public.orq_tasks(project_id,owner_id);
create index if not exists orq_tasks_preferred_owner_idx on public.orq_tasks(preferred_node_id,owner_id);

commit;
