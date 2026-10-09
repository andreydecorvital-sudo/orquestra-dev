"""Agent quality gates are offline and do not need a real AI login."""
import pathlib
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

from orchestration.quality import QualityError, inspect_worktree
from gateway.engine import GatewayError, execute_job


def git(repo, *args):
    subprocess.run(['git', *args], cwd=repo, check=True, capture_output=True)


def init_repo(root):
    repo = root / 'repo'
    repo.mkdir()
    git(repo, 'init', '-q')
    git(repo, 'config', 'user.email', 'test@example.invalid')
    git(repo, 'config', 'user.name', 'Tests')
    (repo / 'README.md').write_text('Original\n')
    git(repo, 'add', '.')
    git(repo, 'commit', '-qm', 'initial')
    return repo


class QualityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        self.repo = init_repo(self.root)

    def test_syntax_and_changed_files(self):
        (self.repo / 'valid.py').write_text('answer = 42\n')
        (self.repo / 'new.py').write_text('def ok():\n    return True\n')
        git(self.repo, 'add', '-N', '--', '.')
        r = inspect_worktree(self.repo)
        self.assertEqual(r['python_syntax_files'], 2)
        self.assertEqual(r['changed_files'], 2)
        self.assertEqual(r['tests'], 'not_run')
        self.assertTrue(r['human_approval_required'])

    def test_invalid_python(self):
        (self.repo / 'invalid.py').write_text('def broken(:\n')
        git(self.repo, 'add', '-N', '--', '.')
        with self.assertRaisesRegex(QualityError, 'Sintaxe Python'):
            inspect_worktree(self.repo)

    def test_whitespace(self):
        (self.repo / 'README.md').write_text('trailing spaces  \n')
        with self.assertRaisesRegex(QualityError, 'diff --check'):
            inspect_worktree(self.repo)

    def test_sensitive_paths_flagged(self):
        folder = self.repo / '.github' / 'workflows'
        folder.mkdir(parents=True)
        (folder / 'deploy.yml').write_text('name: manual\n')
        git(self.repo, 'add', '-N', '--', '.')
        self.assertIn('.github/workflows/deploy.yml',
                      inspect_worktree(self.repo)['risk_flags'])

    def test_node_absence_explicit(self):
        (self.repo / 'a.js').write_text('bad JS !!!\n')
        git(self.repo, 'add', '-N', '--', '.')
        with mock.patch('orchestration.quality.shutil.which', return_value=None):
            report = inspect_worktree(self.repo)
        self.assertEqual(report['javascript_checker'], 'unavailable')
        self.assertEqual(report['javascript_syntax_files'], 0)

    def test_bad_javascript_when_node_available(self):
        (self.repo / 'a.js').write_text('function ({\n')
        git(self.repo, 'add', '-N', '--', '.')
        if shutil.which('node'):
            with self.assertRaisesRegex(QualityError, 'Sintaxe JavaScript'):
                inspect_worktree(self.repo)

    def test_external_symlink_blocked(self):
        with tempfile.TemporaryDirectory() as outside:
            path = pathlib.Path(outside) / 'private.py'
            path.write_text('secret = 123\n')
            link = self.repo / 'untrusted.py'
            try:
                link.symlink_to(path)
            except (OSError, NotImplementedError):
                self.skipTest('No symlinks')
            git(self.repo, 'add', '-N', '--', '.')
            with self.assertRaisesRegex(QualityError, 'simbólico'):
                inspect_worktree(self.repo)


class PatchResilienceTests(unittest.TestCase):
    def test_claude_review_failure_keeps_codex_patch(self):
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder)
            repo = init_repo(root)
            home = root / 'home'
            home.mkdir()
            calls = []
            def fake_cli(provider, prompt, cwd):
                calls.append(provider)
                if calls == ['claude']:
                    return {'output': 'Plano de design', 'ok': True}
                if provider == 'codex':
                    (cwd / 'README.md').write_text('Alteração segura\n')
                    return {'output': 'Pronto', 'ok': True}
                raise GatewayError('Claude offline')
            with mock.patch('gateway.engine.pathlib.Path.home', return_value=home), \
                 mock.patch('gateway.engine.billing_keys_present', return_value=[]):
                with self.assertRaisesRegex(GatewayError, 'patch local preservado'):
                    execute_job({'projects': {'testing': str(repo)},
                                 'allow_execution': True},
                                {'project': 'testing', 'provider': 'joint',
                                 'prompt': 'Make a safe isolated change'}, cli=fake_cli)
            patches = list((home / '.orquestra' / 'artifacts').glob('*.patch'))
            self.assertEqual(len(patches), 1)
            self.assertIn('Alteração segura', patches[0].read_text())
            self.assertEqual((repo / 'README.md').read_text(), 'Original\n')
            self.assertEqual(calls, ['claude', 'codex', 'claude'])

    def test_bad_syntax_preserves_patch_and_blocks_completion(self):
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder)
            repo = init_repo(root)
            home = root / 'home'
            home.mkdir()
            def fake_cli(provider, prompt, cwd):
                (cwd / 'invalid.py').write_text('def broken(:\n')
                return {'output': 'ok', 'ok': True}
            with mock.patch('gateway.engine.pathlib.Path.home', return_value=home), \
                 mock.patch('gateway.engine.billing_keys_present', return_value=[]):
                with self.assertRaisesRegex(GatewayError, 'Quality gate'):
                    execute_job({'projects': {'testing': str(repo)},
                                 'allow_execution': True},
                                {'project': 'testing', 'provider': 'codex',
                                 'prompt': 'Generate a sample invalid function'}, cli=fake_cli)
            patches = list((home / '.orquestra' / 'artifacts').glob('*.patch'))
            self.assertEqual(len(patches), 1)
            self.assertIn('def broken(', patches[0].read_text())
