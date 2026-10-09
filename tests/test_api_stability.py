"""Contract tests for lease fencing and no model/API credential leakage.

SQL/Edge contracts are fast checks. Live DB execution is validated separately.
"""
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]

class ApiStabilityContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sql=(ROOT/'sql/004_execution_fencing.sql').read_text()
        cls.edge=(ROOT/'supabase/functions/orq-worker/index.ts').read_text()
        cls.worker=(ROOT/'runner/agent_worker.py').read_text()

    def test_attempt_fences_both_rpcs(self):
        self.assertEqual(self.sql.count('t.attempts=p_attempt'),2)
        self.assertIn("drop function if exists public.orq_heartbeat_task(uuid,uuid)",self.sql.lower())
        self.assertIn("drop function if exists public.orq_finish_task(uuid,uuid,boolean,text)",self.sql.lower())
        self.assertIn("p_attempt integer",self.sql.lower())

    def test_rpc_is_only_for_server_role(self):
        for name in ('orq_heartbeat_task','orq_finish_task'):
            self.assertIn('grant execute on function public.'+name,self.sql.lower())
        self.assertEqual(self.sql.lower().count('to service_role'),2)
        self.assertIn('from public,anon,authenticated',self.sql.lower())

    def test_node_secret_hash_not_selectable_by_user(self):
        self.assertIn('revoke select on table public.orq_nodes from authenticated',self.sql.lower())
        self.assertIn('grant select(id,owner_id,name,last_seen_at,revoked_at,capabilities,created_at)',self.sql.lower())
        self.assertNotIn('secret_hash',self.sql.split('grant select(')[1].split(')')[0])

    def test_edge_always_sends_attempt_for_claim(self):
        self.assertEqual(self.edge.count('p_attempt:attempt'),2)
        self.assertEqual(self.edge.count("error:'invalid_attempt'"),2)
        self.assertIn("api_version:2",self.edge)
        self.assertIn("'x-orq-request-id':requestId",self.edge)

    def test_worker_protocol_propagates_attempt(self):
        self.assertIn('"action":"heartbeat","task_id":task["id"],"attempt":task["attempt"]',self.worker)
        self.assertIn('"action":"complete","task_id":task["id"],"attempt":task["attempt"]',self.worker)
        self.assertIn('if error.code in (401,403):',self.worker)
        self.assertIn('if error.code == 429:',self.worker)

    def test_no_paid_provider_api(self):
        for string in ('OPENAI_API_KEY','ANTHROPIC_API_KEY','api.openai.com/v1','api.anthropic.com'):
            self.assertNotIn(string,self.edge)
        self.assertIn("auth.getUser(jwt)",self.edge)
        self.assertIn("same(await sha256(secret),node.secret_hash)",self.edge)
