-- Orquestra Hermes as a distinct, owner-scoped kind. No API secrets in DB.
begin;
alter table public.orq_tasks drop constraint if exists orq_tasks_kind_check;
alter table public.orq_tasks add constraint orq_tasks_kind_check
  check (kind in ('diagnose','integrations','codex','claude','joint','hermes'));
alter table public.orq_nodes drop constraint if exists orq_nodes_capabilities_check;
alter table public.orq_nodes add constraint orq_nodes_capabilities_check
  check (capabilities <@ array['diagnose','integrations','codex','claude','joint','hermes']::text[]);
commit;
