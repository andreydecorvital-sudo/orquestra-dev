#!/usr/bin/env bash
# Tests only a disposable local Docker postgres; never connects to CRM.
set -Eeuo pipefail
cd "$(dirname "$0")/../.."
name="orq-chat-ci-$$"
cleanup() { docker rm -f "$name" >/dev/null 2>&1 || true; }
trap cleanup EXIT
docker run -d --rm --name "$name" -e POSTGRES_PASSWORD=ci-temporary \
 postgres:17-alpine >/dev/null
ready=0
for i in $(seq 1 50); do
 if docker logs "$name" 2>&1 | grep -q "PostgreSQL init process complete" && docker exec "$name" pg_isready -U postgres -d postgres >/dev/null 2>&1; then
   ready=1; break
 fi
 sleep 1
done
test "$ready" -eq 1
run_sql() { docker exec -i "$name" psql -X -q -U postgres -d postgres -v ON_ERROR_STOP=1 "$@"; }
scalar() { docker exec "$name" psql -X -qAt -U postgres -d postgres -v ON_ERROR_STOP=1 -c "$1"; }
expect_error() {
 local expected="$1" query="$2" output code
 set +e
 output="$(docker exec "$name" psql -X -qAt -U postgres -d postgres -v ON_ERROR_STOP=1 -c "$query" 2>&1)"
 code=$?
 set -e
 if [ "$code" -eq 0 ] || [[ "$output" != *"$expected"* ]]; then
  echo "Expected SQL rejection $expected but received exit $code" >&2; exit 1
 fi
}
echo '[1/6] Simulated auth roles'
run_sql < tests/chat-db/fixture.sql
echo '[2/6] Original review-only migration in disposable Postgres'
run_sql < sql/008_orquestra_chat_persistence_REVIEW_ONLY.sql
# Stub of the already existing Orquestra projects table, exclusively in CI.
scalar "CREATE TABLE public.orq_projects (id uuid PRIMARY KEY, owner_id uuid NOT NULL REFERENCES auth.users(id)); INSERT INTO public.orq_projects(id,owner_id) VALUES ('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaa01','11111111-1111-4111-8111-111111111111');" >/dev/null
run_sql < sql/009_orquestra_chat_owner_gate.sql
test "$(scalar "SELECT count(*) FROM public.orq_chat_allowed_owners;")" = '1'
test "$(scalar "SELECT count(*) FROM public.orq_chat_allowed_owners WHERE owner_id='11111111-1111-4111-8111-111111111111';")" = '1'
test "$(scalar "SELECT has_table_privilege('authenticated','public.orq_chat_allowed_owners','SELECT');")" = 'f'
test "$(scalar "SELECT has_table_privilege('authenticated','public.orq_chat_allowed_owners','INSERT');")" = 'f'
test "$(scalar "SELECT relrowsecurity FROM pg_class WHERE oid='public.orq_chat_allowed_owners'::regclass;")" = 't'
echo '[3/6] RLS, ownership, and grants'
run_sql < tests/chat-db/assertions.sql
A='11111111-1111-4111-8111-111111111111'
B='22222222-2222-4222-8222-222222222222'
TA='aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'
R1='cccccccc-cccc-4ccc-8ccc-cccccccccccc'
echo '[4/6] Idempotency and cross-owner rejection'
scalar "SET ROLE service_role; SELECT * FROM public.orq_chat_submit('$A','$TA','$R1','olá A');" >/dev/null
test "$(scalar "SELECT count(*) FROM public.orq_chat_turns WHERE owner_id='$A';")" = '1'
expect_error 'ORQ_CHAT_IDEMPOTENCY_CONFLICT' \
 "SET ROLE service_role; SELECT * FROM public.orq_chat_submit('$A','$TA','$R1','modified');"
expect_error 'ORQ_CHAT_THREAD_NOT_FOUND' \
 "SET ROLE service_role; SELECT * FROM public.orq_chat_submit('$B','$TA','eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee','cross-tenant');"
expect_error 'ORQ_CHAT_INVALID_INPUT' \
 "SET ROLE service_role; SELECT * FROM public.orq_chat_submit('$A','$TA','ffffffff-ffff-4fff-8fff-ffffffffffff','   ');"
echo '[5/6] Concurrent replay of same UUID'
R2='abababab-abab-4aba-8aba-abababababab'
query="SET ROLE service_role; SELECT * FROM public.orq_chat_submit('$A','$TA','$R2','concurrent request');"
docker exec "$name" psql -X -qAt -U postgres -d postgres -v ON_ERROR_STOP=1 -c "$query" >/dev/null &
pid1=$!
docker exec "$name" psql -X -qAt -U postgres -d postgres -v ON_ERROR_STOP=1 -c "$query" >/dev/null &
pid2=$!
wait "$pid1"
wait "$pid2"
test "$(scalar "SELECT count(*) FROM public.orq_chat_turns WHERE owner_id='$A';")" = '2'
test "$(scalar "SELECT count(*) FROM public.orq_chat_messages WHERE owner_id='$A';")" = '2'
echo '[6/6] Rate limit and repeated migration guard'
for i in $(seq 1 8); do
 id="$(printf '90000000-0000-4000-8000-%012d' "$i")"
 scalar "SET ROLE service_role; SELECT * FROM public.orq_chat_submit('$A','$TA','$id','message $i');" >/dev/null
done
test "$(scalar "SELECT count(*) FROM public.orq_chat_turns WHERE owner_id='$A';")" = '10'
expect_error 'ORQ_CHAT_RATE_LIMIT' \
 "SET ROLE service_role; SELECT * FROM public.orq_chat_submit('$A','$TA','99999999-9999-4999-8999-999999999999','eleventh');"
set +e
again="$(run_sql < sql/008_orquestra_chat_persistence_REVIEW_ONLY.sql 2>&1)"
code=$?
set -e
test "$code" -ne 0
[[ "$again" == *'BLOCKED: chat objects already exist'* ]]
test "$(scalar "SELECT count(*) FROM public.orq_chat_messages WHERE owner_id='$A';")" = '10'
echo 'PASS: disposable PostgreSQL, RLS two owners, guarded SQL, idempotency, concurrency and quota'

