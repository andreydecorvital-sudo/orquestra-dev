-- PostgreSQL temporary fixture only.
DO $$
BEGIN
 IF (SELECT count(*) FROM pg_catalog.pg_tables WHERE schemaname='public'
  AND tablename IN ('orq_chat_threads','orq_chat_messages','orq_chat_turns')) <> 3
  THEN RAISE EXCEPTION 'missing chat tables'; END IF;
 IF (SELECT count(*) FROM pg_catalog.pg_policies WHERE schemaname='public'
  AND tablename IN ('orq_chat_threads','orq_chat_messages','orq_chat_turns')) <> 3
  THEN RAISE EXCEPTION 'missing chat RLS policies'; END IF;
 IF EXISTS (SELECT 1 FROM pg_catalog.pg_class c
   JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
   WHERE n.nspname='public' AND c.relname IN
   ('orq_chat_threads','orq_chat_messages','orq_chat_turns') AND NOT c.relrowsecurity)
  THEN RAISE EXCEPTION 'RLS disabled'; END IF;
 IF pg_catalog.has_function_privilege('authenticated','public.orq_chat_submit(uuid,uuid,uuid,text)','EXECUTE')
 OR pg_catalog.has_function_privilege('anon','public.orq_chat_submit(uuid,uuid,uuid,text)','EXECUTE')
  THEN RAISE EXCEPTION 'public RPC exposed'; END IF;
 IF pg_catalog.has_table_privilege('authenticated','public.orq_chat_messages','INSERT')
 OR pg_catalog.has_table_privilege('authenticated','public.orq_chat_messages','UPDATE')
 OR pg_catalog.has_table_privilege('authenticated','public.orq_chat_messages','DELETE')
  THEN RAISE EXCEPTION 'client can forge assistant reply'; END IF;
END $$;
INSERT INTO public.orq_chat_threads(id,owner_id,title) VALUES
 ('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa','11111111-1111-4111-8111-111111111111','A'),
 ('bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb','22222222-2222-4222-8222-222222222222','B');
SET ROLE service_role;
SELECT * FROM public.orq_chat_submit('11111111-1111-4111-8111-111111111111','aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa','cccccccc-cccc-4ccc-8ccc-cccccccccccc','olá A');
SELECT * FROM public.orq_chat_submit('22222222-2222-4222-8222-222222222222','bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb','dddddddd-dddd-4ddd-8ddd-dddddddddddd','olá B');
RESET ROLE;
SET ROLE authenticated;
SET request.jwt.claim.sub='11111111-1111-4111-8111-111111111111';
DO $$
BEGIN
 IF (SELECT count(*) FROM public.orq_chat_threads) <> 1
 OR (SELECT count(*) FROM public.orq_chat_messages) <> 1
 OR (SELECT count(*) FROM public.orq_chat_turns) <> 1
 THEN RAISE EXCEPTION 'Owner A isolation failed'; END IF;
END $$;
DO $$
BEGIN
 INSERT INTO public.orq_chat_messages(thread_id,owner_id,role,content)
 VALUES('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa','11111111-1111-4111-8111-111111111111','assistant','fake');
 RAISE EXCEPTION 'untrusted INSERT allowed';
EXCEPTION WHEN insufficient_privilege THEN NULL;
END $$;
SET request.jwt.claim.sub='22222222-2222-4222-8222-222222222222';
DO $$
BEGIN
 IF (SELECT count(*) FROM public.orq_chat_threads) <> 1
 OR (SELECT count(*) FROM public.orq_chat_messages) <> 1
 OR (SELECT count(*) FROM public.orq_chat_turns) <> 1
 THEN RAISE EXCEPTION 'Owner B isolation failed'; END IF;
END $$;
RESET ROLE;
SET ROLE anon;
DO $$
BEGIN
 PERFORM 1 FROM public.orq_chat_threads LIMIT 1;
 RAISE EXCEPTION 'anon read allowed';
EXCEPTION WHEN insufficient_privilege THEN NULL;
END $$;
RESET ROLE;
