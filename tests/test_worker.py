import importlib.util
import json
import pathlib
import tempfile
import unittest
from unittest import mock

FILE=pathlib.Path(__file__).resolve().parents[1] / 'runner' / 'worker.py'
spec=importlib.util.spec_from_file_location('worker',FILE)
worker=importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)


class WorkerTests(unittest.TestCase):
    def test_requires_device_and_mapping(self):
        with tempfile.TemporaryDirectory() as temp:
            path=pathlib.Path(temp)/'config.json'
            path.write_text(json.dumps({'supabase_url':'https://abc.supabase.co', 'node_id':'x'}))
            with self.assertRaisesRegex(ValueError,'node_secret'):
                worker.load_config(path)

    def test_reject_insecure_url(self):
        with tempfile.TemporaryDirectory() as temp:
            path=pathlib.Path(temp)/'config.json'
            path.write_text(json.dumps({'supabase_url':'http://other.example', 'node_id':'x', 'node_secret':'y', 'projects':{'a':'b'}}))
            with self.assertRaisesRegex(ValueError,'HTTPS'):
                worker.load_config(path)

    def test_reject_unmapped_project(self):
        with self.assertRaisesRegex(RuntimeError,'não autorizado'):
            worker.project_directory({'projects':{}},{'project_id':'unknown'})

    def test_unknown_job_rejected(self):
        with mock.patch.object(worker, 'project_directory', return_value=pathlib.Path('/tmp')):
            with self.assertRaisesRegex(RuntimeError,'não autorizado'):
                worker.execute({}, {'kind':'shell','project_id':'x'})

    def test_safe_github_remote_strips_credentials(self):
        self.assertEqual(worker.safe_github_remote('https://user:secret@github.com/example/vitalhub.git'), 'example/vitalhub')
        self.assertEqual(worker.safe_github_remote('git@github.com:example/vitalhub.git'), 'example/vitalhub')
        self.assertIn('ocultado',worker.safe_github_remote('https://token@other.com/a/b.git'))

    def test_integration_scan_does_not_read_secrets(self):
        with tempfile.TemporaryDirectory() as temp:
            import subprocess
            path=pathlib.Path(temp)
            subprocess.run(['git','init',temp],capture_output=True,check=True)
            subprocess.run(['git','-C',temp,'remote','add','origin',
                            'https://username:SECRET@github.com/example/vitalhub.git'],check=True)
            for name in ('supabase/config.toml','tools/argo-print-agent/Program.cs',
                         'tools/argo-print-desktop/LocalStatus.cs'):
                file=path/name; file.parent.mkdir(parents=True,exist_ok=True);file.write_text('SECRET')
            result=worker.inspect_integrations(path)
            self.assertIn('example/vitalhub',result)
            self.assertIn('Argoplace Print Agent no código: encontrado',result)
            self.assertNotIn('SECRET',result)
            self.assertIn('Supabase remoto: não consultado',result)

    def test_print_diagnostic_reveals_no_pairing_info(self):
        with tempfile.TemporaryDirectory() as temp:
            root=pathlib.Path(temp)
            (root/'ARGO'/'Print').mkdir(parents=True)
            (root/'ARGO'/'Print'/'agent-state.json').write_text('{"protectedSecret":"PRIVATE"}')
            with mock.patch.object(worker,'command',return_value=(0,'STATE : 4 RUNNING')):
                result=worker.argo_print_status(program_data=temp,program_files=temp,is_windows=True)
            self.assertIn('em execução',result)
            self.assertIn('Arquivo de estado local: presente',result)
            self.assertNotIn('PRIVATE',result)

    def test_codex_disabled_by_default(self):
        with self.assertRaisesRegex(RuntimeError,'desligado'):
            worker.execute_codex({},pathlib.Path('/tmp'),{'id':'x'})

    def test_diagnose_git_repo(self):
        with tempfile.TemporaryDirectory() as temp:
            import subprocess
            subprocess.run(['git','init',temp],capture_output=True,check=True)
            output=worker.diagnose(pathlib.Path(temp))
            self.assertIn('git status',output)


if __name__=='__main__': unittest.main()
