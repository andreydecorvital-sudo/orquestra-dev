"""Readiness preflight must be safe and must never claim live execution."""
import json
import pathlib
import tempfile
import unittest

from runner.preflight import inspect_readiness


class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        self.config = self.root / "private.json"
        self.git = self.root / "repo"
        self.git.mkdir()
        (self.git / ".git").mkdir()
        self.config.write_text('{"private":"NEVER-ECHO"}', encoding="utf-8")
        self.data = {
            "allow_execution": False,
            "node_secret": "NEVER-ECHO-SECRET",
            "projects": {"internal-id": {"slug": "pilot", "path": str(self.git)}},
        }

    def inspect(self, overrides=None, *, cli=None):
        return inspect_readiness(self.config,
            load_fn=lambda _p: overrides if overrides is not None else self.data,
            cli_fn=cli or (lambda _p: {"login": "not_authenticated"}))

    def test_missing_config_blocks_without_invoking_loader(self):
        outcome = inspect_readiness(self.root / 'does-not-exist',
                                    load_fn=lambda _: self.fail('loader invoked'),
                                    cli_fn=lambda _: self.fail('CLI invoked'))
        self.assertEqual(outcome['status'], 'blocked')
        self.assertEqual(outcome['checks']['config'], 'not_found')

    def test_invalid_config_does_not_show_exception_text(self):
        def bad(_):
            raise ValueError('node_secret NEVER-ECHO')
        outcome = inspect_readiness(self.config, load_fn=bad, cli_fn=lambda _: {})
        self.assertEqual(outcome['checks']['config'], 'invalid')
        self.assertNotIn('NEVER-ECHO', json.dumps(outcome))

    def test_diagnostics_ready_does_not_call_cli(self):
        outcome = self.inspect(cli=lambda _: self.fail('CLI should not run'))
        self.assertEqual(outcome['status'], 'diagnostics_ready_locally')
        self.assertEqual(outcome['checks']['repository'], 'mapped_local_git')
        self.assertFalse(outcome['end_to_end_verified'])
        self.assertEqual(outcome['backend'], 'not_checked')
        self.assertNotIn('NEVER-ECHO', json.dumps(outcome))
        self.assertNotIn(str(self.git), json.dumps(outcome))
        self.assertNotIn('internal-id', json.dumps(outcome))

    def test_missing_mapping_blocks(self):
        result = self.inspect({**self.data, 'projects': {}})
        self.assertEqual(result['checks']['repository'], 'missing_mapping')
        self.assertEqual(result['status'], 'blocked')

    def test_local_git_required(self):
        (self.git / '.git').rmdir()
        result = self.inspect()
        self.assertEqual(result['checks']['repository'], 'not_git_directory')
        self.assertEqual(result['status'], 'blocked')

    def test_available_code_cli_not_full_success(self):
        providers = []
        def fake_cli(provider):
            providers.append(provider)
            return {'login': 'authenticated' if provider == 'codex' else 'not_authenticated'}
        result = self.inspect({**self.data, 'allow_execution': True}, cli=fake_cli)
        self.assertEqual(providers, ['codex', 'claude'])
        self.assertEqual(result['status'], 'code_ready_locally')
        self.assertEqual(result['local_providers'], ['codex'])
        self.assertFalse(result['end_to_end_verified'])
        self.assertEqual(result['tests'], 'not_run')

    def test_no_provider_means_login_required(self):
        result = self.inspect({**self.data, 'allow_execution': True})
        self.assertEqual(result['status'], 'login_required')

    def test_bad_repo_structure_does_not_expose_path(self):
        result = self.inspect({**self.data, 'projects': {'bad': 'private path'}})
        self.assertEqual(result['checks']['repository'], 'invalid_mapping')
        self.assertNotIn('private path', json.dumps(result))


if __name__ == '__main__':
    unittest.main()
