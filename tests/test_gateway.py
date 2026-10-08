"""No network, no CLI logins required."""
import importlib
import json
import os
import pathlib
import tempfile
import threading
import subprocess
import unittest
from unittest.mock import patch
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from gateway.engine import (API_ENV, GatewayError, billing_keys_present, clean_env,
                            validate_job, run_cli, execute_job)
from gateway.server import build_handler


class GatewayTests(unittest.TestCase):
    def test_billing_env_scrubbed(self):
        env = clean_env({'PATH': 'X', 'OPENAI_API_KEY': 'secret', 'ANTHROPIC_API_KEY': 'x',
                         'ANTHROPIC_AUTH_TOKEN':'x', 'ORQ_LOCAL_TOKEN': 'abc'})
        self.assertEqual(env, {'PATH': 'X', 'ORQ_LOCAL_TOKEN':'abc'})

    def test_detect_billing_variables(self):
        self.assertEqual(billing_keys_present({'OPENAI_API_KEY':'', 'ANTHROPIC_API_KEY':'abc'}),
                         ['ANTHROPIC_API_KEY'])

    def test_validation_blocks_unknown_provider(self):
        with self.assertRaises(GatewayError):
            validate_job({'project':'test-repo', 'provider':'browser-cookie', 'prompt':'do this safely'})

    def test_validation_blocks_bad_project_and_prompt(self):
        for project in ['../prod', 'C:/Windows', '']: 
            with self.subTest(project=project), self.assertRaises(GatewayError):
                validate_job({'project':project, 'provider':'codex', 'prompt':'do this safely'})
        with self.assertRaises(GatewayError):
            validate_job({'project':'testing', 'provider':'claude', 'prompt':'short'})

    def test_execution_defaults_disabled(self):
        with tempfile.TemporaryDirectory() as td:
            path=pathlib.Path(td)
            (path/'.git').mkdir()
            with self.assertRaisesRegex(GatewayError, 'Execução desativada'):
                execute_job({'projects':{'testing':str(path)}, 'allow_execution':False},
                            {'project':'testing', 'provider':'codex', 'prompt':'Implement a safe test'})

    def test_codex_invocation_stdin_no_shell(self):
        with patch('gateway.engine.shutil.which', return_value='C:/codex.exe'), \
             patch('gateway.engine.subprocess.run') as proc:
            proc.return_value.returncode=0
            proc.return_value.stdout='ok'
            result=run_cli('codex', 'say hi', pathlib.Path('.'), seconds=20)
            self.assertEqual(result['output'], 'ok')
            args, kwargs=proc.call_args
            self.assertEqual(args[0][:3], ['codex','exec','--sandbox'])
            self.assertFalse(kwargs['shell'])
            self.assertEqual(kwargs['input'], 'say hi')

    def test_claude_invocation_plan_mode(self):
        with patch('gateway.engine.shutil.which', return_value='C:/claude.exe'), \
             patch('gateway.engine.subprocess.run') as proc:
            proc.return_value.returncode=0
            proc.return_value.stdout='planned'
            result=run_cli('claude', 'draw this', pathlib.Path('.'))
            self.assertTrue(result['ok'])
            args, kwargs=proc.call_args
            self.assertIn('plan', args[0]); self.assertIn('-p', args[0])
            self.assertFalse(kwargs['shell'])

    def test_http_requires_authorization(self):
        handler=build_handler({'allow_execution':False}, 'x'*40)
        server=ThreadingHTTPServer(('127.0.0.1',0),handler)
        thread=threading.Thread(target=server.serve_forever, daemon=True);thread.start()
        try:
            port=server.server_port
            for method in ['GET','POST']:
                with self.subTest(method=method):
                    req=Request(f'http://127.0.0.1:{port}/v1/tasks', data=b'{}' if method=='POST' else None, method=method)
                    with self.assertRaises(HTTPError) as c: urlopen(req,timeout=3)
                    self.assertEqual(c.exception.code,401)
            req=Request(f'http://127.0.0.1:{port}/v1/status',headers={'Authorization':'Bearer '+'x'*40})
            with patch('gateway.server.cli_status',return_value={'installed':False,'login':'unavailable'}):
                with urlopen(req,timeout=3) as f:
                    body=json.loads(f.read())
            self.assertEqual(body['billing'],'subscription_only')
            self.assertFalse(body['execution_enabled'])
        finally:
            server.shutdown();server.server_close();thread.join(timeout=3)

    def test_codex_patch_persists_and_worktree_is_cleaned(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td)
            repo=root/'repo';repo.mkdir()
            commands=[['git','init','-q'],['git','config','user.email','test@example.invalid'],
                      ['git','config','user.name','Tests']]
            for argv in commands:
                self.assertEqual(subprocess.run(argv,cwd=repo,capture_output=True).returncode,0)
            (repo/'README.md').write_text('Original\n')
            subprocess.run(['git','add','.'],cwd=repo,check=True,capture_output=True)
            subprocess.run(['git','commit','-m','initial','-q'],cwd=repo,check=True,capture_output=True)
            def fake_cli(provider, prompt, cwd):
                (cwd/'new-file.txt').write_text('Arquivo novo\n')
                (cwd/'README.md').write_text('Alterado\n')
                return {'provider':provider,'ok':True,'output':'Concluído'}
            fake_home=root/'home'; fake_home.mkdir()
            old_home=pathlib.Path.home
            with patch('gateway.engine.pathlib.Path.home',return_value=fake_home), \
                 patch('gateway.engine.billing_keys_present',return_value=[]):
                result=execute_job({'allow_execution':True,'projects':{'testing':str(repo)}},
                                   {'project':'testing','provider':'codex','prompt':'Create and modify some files'},cli=fake_cli)
            self.assertEqual(result['status'],'review_required')
            self.assertIn('new-file.txt',result['patch'])
            self.assertIn('README.md',result['patch'])
            self.assertTrue(pathlib.Path(result['artifact_path']).exists())
            self.assertEqual(pathlib.Path(result['artifact_path']).read_text(),result['patch'])
            self.assertEqual((repo/'README.md').read_text(),'Original\n')
            self.assertFalse((repo/'new-file.txt').exists())

    def test_block_unrecognized_cli(self):
        with self.assertRaises(GatewayError):
            run_cli('paid-api','test prompt',pathlib.Path('.'))


if __name__=='__main__': unittest.main()
