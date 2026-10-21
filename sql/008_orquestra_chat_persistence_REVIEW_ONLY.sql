-- REVIEW ONLY. Not applied. Supabase Chatbot shares Auth, quotas and service_role with CRM.
-- Explicit DB authorization, two-account RLS test, backup/recovery plan and security
-- review required before executing. Does not modify any CRM/legacy orq_ object.
BEGIN;
DO $preflight$
BEGIN
  IF pg_catalog.to_regclass('auth.users') IS NULL
     OR pg_catalog.to_regclass('public.orq_nodes') IS NULL THEN
    RAISE EXCEPTION 'BLOCKED: expected Orquestra/Chatbot schema missing';
  END IF;
  IF pg_catalog.to_regclass('public.orq_chat_threads') IS NOT NULL
     OR pg_catalog.to_regclass('public.orq_chat_messages') IS NOT NULL
     OR pg_catalog.to_regclass('public.orq_chat_turns') IS NOT NULL
     OR pg_catalog.to_regprocedure('public.orq_chat_submit(uuid,uuid,uuid,text)') IS NOT NULL THEN
    RAISE EXCEPTION 'BLOCKED: chat objects already exist; do not repeat migration';
  END IF;
END;
$preflight$;

CREATE TABLE public.orq_chat_threads (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  title text NOT NULL DEFAULT 'Nova conversa'
    CHECK (char_length(title) BETWEEN 1 AND 80),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (id, owner_id)
);
CREATE INDEX orq_chat_threads_recent_idx
  ON public.orq_chat_threads (owner_id, updated_at DESC);

CREATE TABLE public.orq_chat_messages (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  thread_id uuid NOT NULL,
  owner_id uuid NOT NULL,
  role text NOT NULL CHECK (role IN ('user','assistant')),
  content text NOT NULL CHECK (char_length(content) BETWEEN 1 AND 12000),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (id, owner_id),
  CONSTRAINT orq_chat_messages_thread_owner FOREIGN KEY (thread_id, owner_id)
    REFERENCES public.orq_chat_threads(id, owner_id) ON DELETE CASCADE
);
CREATE INDEX orq_chat_messages_recent_idx
  ON public.orq_chat_messages (owner_id, thread_id, created_at, id);

CREATE TABLE public.orq_chat_turns (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  thread_id uuid NOT NULL,
  owner_id uuid NOT NULL,
  message_id uuid NOT NULL,
  client_request_id uuid NOT NULL,
  status text NOT NULL DEFAULT 'blocked'
    CHECK (status IN ('blocked','queued','running','completed','failed')),
  blocker_code text CHECK (blocker_code IS NULL OR blocker_code IN
    ('provider_not_connected','quota_exhausted','approval_required','executor_unavailable')),
  provider text,
  created_at timestamptz NOT NULL DEFAULT now(),
  finished_at timestamptz,
  CONSTRAINT orq_chat_turns_thread_owner FOREIGN KEY (thread_id, owner_id)
    REFERENCES public.orq_chat_threads(id, owner_id) ON DELETE CASCADE,
  CONSTRAINT orq_chat_turns_message_owner FOREIGN KEY (message_id, owner_id)
    REFERENCES public.orq_chat_messages(id, owner_id) ON DELETE CASCADE,
  UNIQUE (owner_id, client_request_id),
  UNIQUE (owner_id, message_id)
);
CREATE INDEX orq_chat_turns_recent_idx
  ON public.orq_chat_turns(owner_id, thread_id, created_at DESC);

ALTER TABLE public.orq_chat_threads ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.orq_chat_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.orq_chat_turns ENABLE ROW LEVEL SECURITY;

-- The Edge Function validates a human JWT then performs owner-scoped writes.
-- Authenticated web clients have read-only access; they cannot fake AI messages.
REVOKE ALL ON public.orq_chat_threads, public.orq_chat_messages,
  public.orq_chat_turns FROM PUBLIC, anon, authenticated;
GRANT SELECT ON public.orq_chat_threads, public.orq_chat_messages,
  public.orq_chat_turns TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.orq_chat_threads,
  public.orq_chat_messages, public.orq_chat_turns TO service_role;

CREATE POLICY orq_chat_threads_read ON public.orq_chat_threads
  FOR SELECT TO authenticated USING (owner_id = (SELECT auth.uid()));
CREATE POLICY orq_chat_messages_read ON public.orq_chat_messages
  FOR SELECT TO authenticated USING (owner_id = (SELECT auth.uid()));
CREATE POLICY orq_chat_turns_read ON public.orq_chat_turns
  FOR SELECT TO authenticated USING (owner_id = (SELECT auth.uid()));

-- Atomic message + turn creation. Only the private Edge Function (service_role)
-- may call this RPC, *after* getUser(JWT) verifies the current owner.
-- Per-owner lock prevents concurrent duplicate submissions and rate-limit races.
CREATE FUNCTION public.orq_chat_submit(
  p_owner_id uuid,
  p_thread_id uuid,
  p_request_id uuid,
  p_content text
) RETURNS TABLE (turn_id uuid, message_id uuid, turn_status text, blocker_code text)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE
  v_thread_owner uuid;
  v_existing record;
  v_message_id uuid;
  v_turn_id uuid;
  v_count integer;
BEGIN
  IF p_owner_id IS NULL OR p_thread_id IS NULL OR p_request_id IS NULL
     OR p_content IS NULL OR char_length(btrim(p_content)) = 0
     OR char_length(p_content) > 12000 THEN
    RAISE EXCEPTION 'ORQ_CHAT_INVALID_INPUT';
  END IF;

  PERFORM pg_catalog.pg_advisory_xact_lock(
    pg_catalog.hashtextextended('orq-chat-owner:' || p_owner_id::text, 0)
  );

  SELECT t.owner_id INTO v_thread_owner
  FROM public.orq_chat_threads t WHERE t.id = p_thread_id;
  IF v_thread_owner IS DISTINCT FROM p_owner_id THEN
    RAISE EXCEPTION 'ORQ_CHAT_THREAD_NOT_FOUND';
  END IF;

  SELECT x.id, x.thread_id, x.status, x.blocker_code, m.id AS msg_id,
         m.content AS original_content
    INTO v_existing
    FROM public.orq_chat_turns x
    JOIN public.orq_chat_messages m ON m.id = x.message_id
                                   AND m.owner_id = x.owner_id
   WHERE x.owner_id = p_owner_id AND x.client_request_id = p_request_id;
  IF FOUND THEN
    IF v_existing.thread_id <> p_thread_id
       OR v_existing.original_content <> p_content THEN
      RAISE EXCEPTION 'ORQ_CHAT_IDEMPOTENCY_CONFLICT';
    END IF;
    RETURN QUERY SELECT v_existing.id::uuid, v_existing.msg_id::uuid,
                        v_existing.status::text, v_existing.blocker_code::text;
    RETURN;
  END IF;

  SELECT count(*) INTO v_count FROM public.orq_chat_turns
   WHERE owner_id = p_owner_id AND created_at > now() - interval '1 minute';
  IF v_count >= 10 THEN RAISE EXCEPTION 'ORQ_CHAT_RATE_LIMIT'; END IF;

  SELECT count(*) INTO v_count FROM public.orq_chat_turns
   WHERE owner_id = p_owner_id AND created_at > now() - interval '1 day';
  IF v_count >= 300 THEN RAISE EXCEPTION 'ORQ_CHAT_RATE_LIMIT'; END IF;

  INSERT INTO public.orq_chat_messages (thread_id, owner_id, role, content)
    VALUES (p_thread_id, p_owner_id, 'user', p_content)
    RETURNING id INTO v_message_id;
  -- This is an honest blocked turn, not a fake AI result or paid API call.
  INSERT INTO public.orq_chat_turns
      (thread_id, owner_id, message_id, client_request_id, status, blocker_code)
    VALUES (p_thread_id, p_owner_id, v_message_id, p_request_id,
            'blocked', 'provider_not_connected')
    RETURNING id INTO v_turn_id;
  UPDATE public.orq_chat_threads SET updated_at = now()
   WHERE id = p_thread_id AND owner_id = p_owner_id;

  RETURN QUERY SELECT v_turn_id, v_message_id, 'blocked'::text,
                      'provider_not_connected'::text;
END;
$$;
REVOKE ALL ON FUNCTION public.orq_chat_submit(uuid,uuid,uuid,text)
  FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.orq_chat_submit(uuid,uuid,uuid,text)
  TO service_role;

COMMIT;
