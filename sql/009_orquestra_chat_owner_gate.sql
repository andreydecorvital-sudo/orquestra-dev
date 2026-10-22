-- Additive Orquestra-only authorization table. Does not modify CRM/Auth rows.
-- Seed exactly the existing owner of Orquestra projects. Abort if ambiguous.
BEGIN;
DO $preflight$
BEGIN
  IF pg_catalog.to_regclass('public.orq_chat_threads') IS NULL
     OR pg_catalog.to_regclass('public.orq_projects') IS NULL
     OR pg_catalog.to_regclass('auth.users') IS NULL THEN
    RAISE EXCEPTION 'ORQ_CHAT_GATE_MISSING_DEPENDENCY';
  END IF;
  IF pg_catalog.to_regclass('public.orq_chat_allowed_owners') IS NOT NULL THEN
    RAISE EXCEPTION 'ORQ_CHAT_GATE_ALREADY_EXISTS';
  END IF;
  IF (SELECT COUNT(DISTINCT owner_id) FROM public.orq_projects) <> 1 THEN
    RAISE EXCEPTION 'ORQ_CHAT_GATE_AMBIGUOUS_OWNER';
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM public.orq_projects p
    JOIN auth.users u ON u.id = p.owner_id
  ) THEN
    RAISE EXCEPTION 'ORQ_CHAT_GATE_OWNER_NOT_IN_AUTH';
  END IF;
END
$preflight$;

CREATE TABLE public.orq_chat_allowed_owners (
  owner_id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  authorized_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE public.orq_chat_allowed_owners ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.orq_chat_allowed_owners FROM PUBLIC, anon, authenticated;
GRANT SELECT ON TABLE public.orq_chat_allowed_owners TO service_role;
-- No client RLS policies: browser clients cannot list, forge or change grants.
INSERT INTO public.orq_chat_allowed_owners(owner_id)
  SELECT DISTINCT p.owner_id
  FROM public.orq_projects p
  JOIN auth.users u ON u.id = p.owner_id;

DO $assert$
BEGIN
  IF (SELECT COUNT(*) FROM public.orq_chat_allowed_owners) <> 1 THEN
    RAISE EXCEPTION 'ORQ_CHAT_GATE_BAD_SEED';
  END IF;
END
$assert$;
COMMIT;
