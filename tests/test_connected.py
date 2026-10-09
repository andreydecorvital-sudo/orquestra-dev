"""Contract tests for v1.0 queue and lightweight subscription-only runner."""
import json
import pathlib
import tempfile
import unittest
from unittest import mock
from runner.agent_worker import load_config, advertised_capabilities, summarise, work_once
from gateway.engine import GatewayError

ROOT=pathlib.Path(__file__).resolve().parents[1]

class ConnectedTests(unittest.TestCase):
    def test_config_requires_https(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)/'cfg.json'
            p.write_text(json.dumps({'supabase_url':'http://fake.tld','node_id':'a'*36,'node_secret':'a'*64,'projects':{}}))
            with self.assertRaises(ValueError):load_config(p)

    def test_config_disables_execution_by_default(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)/'cfg.json'
            p.write_text(json.dumps({'supabase_url':'https://example.supabase.co',
              'node_id':'a'*36,'node_secret':'b'*64,'projects':{}}))
            self.assertFalse(load_config(p)['allow_execution'])

    def test_offline_only_diagnostics(self):
        self.assertEqual(['diagnose','integrations'],advertised_capabilities({'allow_execution':False}))

    def test_no_unauthenticated_cli_job(self):
        with mock.patch('runner.agent_worker.cli_status',return_value={'installed':True,'login':'not_authenticated'}):
            self.assertEqual(['diagnose','integrations'],advertised_capabilities({'allow_execution':True}))

    def test_joint_only_when_both_logged_in(self):
        def states(provider):return {'login':'authenticated' if provider=='codex' else 'not_authenticated'}
        with mock.patch('runner.agent_worker.cli_status',side_effect=states):
            self.assertEqual(['diagnose','integrations','codex'],advertised_capabilities({'allow_execution':True}))
        with mock.patch('runner.agent_worker.cli_status',return_value={'login':'authenticated'}):
            self.assertIn('joint',advertised_capabilities({'allow_execution':True}))

    def test_remote_project_must_be_mapped(self):
        with self.assertRaises(GatewayError):
            work_once({'projects':{},'allow_execution':False},{'id':'task','kind':'codex','project_id':'unknown'})

    def test_remote_kind_allowlist(self):
        with self.assertRaises(GatewayError):
            work_once({'projects':{'id':{'slug':'abc','path':'/tmp/abc'}},'allow_execution':True},
                {'id':'task','kind':'shell','project_id':'id'})

    def test_gateway_engine_receives_only_allowlisted_project(self):
        received=[]
        def engine(config,payload):
            received.append((config,payload))
            return {'provider':'joint','stages':[]}
        def send(config,payload): return {'ok':True}
        output=work_once({'projects':{'uuid':{'slug':'foo','path':'/tmp/foo'}},'allow_execution':True},
            {'id':'task-1','kind':'joint','project_id':'uuid','attempt':1,'title':'Uma tarefa','instructions':'Código'},
            send=send,engine=engine,heartbeat_interval=.01)
        self.assertEqual(output['provider'],'joint')
        self.assertEqual(received[0][1]['project'],'foo')
        self.assertEqual(received[0][1]['provider'],'joint')

    def test_summary_does_not_return_patch_body(self):
        result={'provider':'joint','patch':'SENSITIVE-DIFF','artifact_path':'/home/user/.orquestra/secret.patch',
                 'stages':[{'role':'claude','step':'review','result':'SENSITIVE-FULL-REVIEW'}]}
        result_text=summarise(result)
        self.assertNotIn('SENSITIVE-DIFF',result_text)
        self.assertNotIn('SENSITIVE-FULL-REVIEW',result_text)
        self.assertNotIn('/home/user/',result_text)

    def test_schema_has_private_rpc_and_lifecycle(self):
        s=(ROOT/'sql/003_durable_execution.sql').read_text()
        for token in ('orq_heartbeat_task','orq_finish_task','lease_expires_at',
                      'for update skip locked','revoke all on function','to service_role',
                      'enable row level security','q.kind = any(v_capabilities)'):
            self.assertIn(token,s.lower())

    def test_edge_has_server_side_auth(self):
        code=(ROOT/'supabase/functions/orq-worker/index.ts').read_text()
        for token in ("admin.auth.getUser(jwt)", "same(await sha256(secret),node.secret_hash)",
                      "admin.rpc('orq_finish_task'", "admin.rpc('orq_heartbeat_task'", "action==='capabilities'"):
            self.assertIn(token,code)
        self.assertNotIn("'access-control-allow-origin':'*'",code)

    def test_web_only_public_setup_key(self):
        code=(ROOT/'web-live/app.js').read_text()
        self.assertIn('sb_publishable_',code)
        self.assertIn("client.from('orq_tasks').insert",code)
        self.assertIn('service_role',code)
        self.assertNotIn('SUPABASE_SERVICE_ROLE_KEY',code)
        self.assertNotIn('ANTHROPIC_API_KEY',code)

if __name__=='__main__':unittest.main()
