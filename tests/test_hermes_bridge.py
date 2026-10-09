"""Hermes integration: loopback-only, provider never billed silently."""
import io
import json
import pathlib
import tempfile
import unittest
from unittest import mock

from gateway.engine import GatewayError
from gateway.hermes_bridge import api_key, safe_model, hermes_ready, run_hermes
from runner.agent_worker import advertised_capabilities, work_once, summarise

ROOT=pathlib.Path(__file__).resolve().parents[1]

class HermesBridgeTests(unittest.TestCase):
    def make_env(self, p):
        (p/'.env').write_text("API_SERVER_ENABLED=true\nAPI_SERVER_HOST=127.0.0.1\nAPI_SERVER_PORT=8642\nAPI_SERVER_KEY="+'X'*48)
    
    def test_local_key_and_host_required(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)
            self.make_env(p)
            with mock.patch.dict('os.environ',{'HERMES_HOME':d}):
                self.assertEqual(api_key(),'X'*48)
                (p/'.env').write_text("API_SERVER_ENABLED=true\nAPI_SERVER_HOST=0.0.0.0\nAPI_SERVER_KEY="+'X'*48)
                with self.assertRaises(GatewayError):api_key()

    def test_status_requires_explicit_opt_in(self):
        with mock.patch('gateway.hermes_bridge.api_key',side_effect=AssertionError('should not read')):
            self.assertFalse(hermes_ready({'allow_execution':False,'allow_hermes_planning':True}))
        self.assertNotIn('hermes',advertised_capabilities({'allow_execution':True}))
    
    def test_tool_preflight_fails_closed(self):
        def respond(key,path,**kwargs):
            if path=="/v1/toolsets":return [{"name":"hermes-api-server","enabled":True,"tools":["terminal"]}]
            return {"data":[{"id":"hermes-agent"}]}
        with mock.patch('gateway.hermes_bridge._request',side_effect=respond):
            with self.assertRaisesRegex(GatewayError,'ferramentas ativas'):safe_model("K"*48)
        with mock.patch('gateway.hermes_bridge._request',return_value={"unexpected":1}):
            with self.assertRaises(GatewayError):safe_model("K"*48)

    def test_model_only_mode_produces_text(self):
        sent=[]
        def respond(key,path,**kwargs):
            sent.append((path,kwargs))
            if path=="/v1/toolsets":return [{"name":"hermes-api-server","enabled":True,"tools":[]}]
            if path=="/v1/models":return {"data":[{"id":"hermes-agent"}]}
            return {"choices":[{"message":{"content":"Plano: revisar testes; nenhum push."}}]}
        with mock.patch('gateway.hermes_bridge.api_key',return_value="K"*48), \
             mock.patch('gateway.hermes_bridge._request',side_effect=respond):
            t=run_hermes({'allow_execution':True,'allow_hermes_planning':True},
                "Revisar integração e sugerir testes",'a'*36)
        self.assertEqual(t['provider'],'hermes')
        self.assertIn('revisar testes',summarise(t))
        self.assertEqual(sent[-1][0],'/v1/chat/completions')
        self.assertFalse(sent[-1][1]['payload']['stream'])

    def test_worker_dispatch_and_lease(self):
        calls=[]
        def send(cfg,payload):
            calls.append(payload)
            return {'ok':True}
        def hermes(cfg,prompt,task):
            return {'provider':'hermes','output':'Revisão sem comandos.','stages':[]}
        task={'id':'a'*36,'kind':'hermes','attempt':1,'project_id':'id',
              'title':'Analisar segurança','instructions':'Elencar critérios de aceitação'}
        result=work_once({'allow_execution':True,'allow_hermes_planning':True,
           'projects':{'id':{'slug':'safe','path':'/tmp/safe'}}},task,
           send=send,hermes_engine=hermes,engine=lambda *_:self.fail('No Codex CLI'))
        self.assertEqual(result['provider'],'hermes')

    def test_public_contract(self):
        self.assertIn("'hermes'",(ROOT/'supabase/functions/orq-worker/index.ts').read_text())
        self.assertIn("value=\"hermes\"",(ROOT/'web-live/index.html').read_text())
        self.assertIn("orq_tasks_kind_check",(ROOT/'sql/005_hermes_kind.sql').read_text())
        js=(ROOT/'web-live/app.js').read_text()
        self.assertIn("'hermes'",js)
