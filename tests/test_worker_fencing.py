"""Worker heartbeat must be fenced to the task's current attempt."""
import time
import unittest
from unittest.mock import patch

from runner.agent_worker import work_once
from gateway.engine import GatewayError

class FencingWorkerTests(unittest.TestCase):
    def test_heartbeat_includes_claim_attempt(self):
        calls=[]
        def send(cfg,payload):
            calls.append(payload)
            return {'ok':True}
        def engine(cfg,payload):
            time.sleep(.045)
            return {'provider':'joint','stages':[]}
        task={'id':'task-1','kind':'joint','project_id':'remote',
              'attempt':2,'title':'Teste de lease','instructions':'Não editar arquivo'}
        work_once({'allow_execution':True,'projects':{'remote':{'slug':'safe','path':'/tmp/safe'}}},
                  task,send=send,engine=engine,heartbeat_interval=.005)
        beats=[c for c in calls if c['action']=='heartbeat']
        self.assertGreater(len(beats),0)
        self.assertTrue(all(c['attempt']==2 for c in beats))

    def test_missing_attempt_rejected_before_engine(self):
        task={'id':'task-1','kind':'joint','project_id':'remote',
              'title':'Teste de lease','instructions':'Não editar arquivo'}
        with self.assertRaisesRegex(GatewayError,'Tentativa de execução inválida'):
            work_once({'allow_execution':True,'projects':{'remote':{'slug':'safe','path':'/tmp/safe'}}},
                      task,engine=lambda *_: self.fail('must not execute'))
