-- Execute SOMENTE no projeto Supabase isolado do Orquestra Dev.
-- Permite o diagnóstico local somente leitura e não altera dados de produção.
alter table public.orq_tasks drop constraint if exists orq_tasks_kind_check;
alter table public.orq_tasks
  add constraint orq_tasks_kind_check
  check (kind in ('diagnose','codex','integrations'));
