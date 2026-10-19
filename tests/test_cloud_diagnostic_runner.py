"""Cloud pilot fails closed and never enables execution or leaks credentials."""
import pathlib
import tempfile
import unittest
from unittest import mock

from cloud.diagnostic_runner import (
    CloudPilotError, PUBLIC_PILOT_REPO,
    clone_public_pilot, config_from_environment,
)


class CloudDiagnosticPilotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.checkout = pathlib.Path(self.temp.name) / "pilot"
        self.env = {
            "ORQ_CLOUD_SUPABASE_URL": "https://example.supabase.co",
            "ORQ_CLOUD_NODE_ID": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "ORQ_CLOUD_NODE_SECRET": "b" * 64,
            "ORQ_CLOUD_PROJECT_ID": "cccccccc-cccc-cccc-cccc-cccccccccccc",
        }

    def test_missing_configuration_blocks(self):
        with self.assertRaises(CloudPilotError):
            config_from_environment({}, self.checkout)

    def test_untrusted_supabase_url_blocks(self):
        with self.assertRaises(CloudPilotError):
            config_from_environment({**self.env, "ORQ_CLOUD_SUPABASE_URL": "http://localhost:54321"}, self.checkout)

    def test_cannot_enable_code_or_hermes(self):
        with self.assertRaisesRegex(CloudPilotError, "IA"):
            config_from_environment({**self.env, "ORQ_CLOUD_ENABLE_CODE": "true"}, self.checkout)

    def test_rejects_unapproved_repository(self):
        with self.assertRaisesRegex(CloudPilotError, "restrito"):
            config_from_environment({**self.env, "ORQ_CLOUD_PILOT_REPOSITORY": "https://github.com/example/private.git"}, self.checkout)

    def test_no_external_ai_even_with_valid_credentials(self):
        cfg = config_from_environment(self.env, self.checkout)
        self.assertFalse(cfg["allow_execution"])
        self.assertFalse(cfg["allow_hermes_planning"])
        self.assertEqual(list(cfg["projects"].values())[0]["slug"], "orquestra_pilot")

    def test_bad_node_id_blocks(self):
        with self.assertRaises(CloudPilotError):
            config_from_environment({**self.env, "ORQ_CLOUD_NODE_ID": "invalid"}, self.checkout)

    def test_clone_uses_fixed_repo_without_shell_or_prompt(self):
        def mock_clone(args, **kwargs):
            self.assertEqual(args[:2], ["git", "clone"])
            self.assertIn(PUBLIC_PILOT_REPO, args)
            self.assertFalse(kwargs.get("shell", False))
            self.assertEqual(kwargs["env"]["GIT_TERMINAL_PROMPT"], "0")
            self.checkout.mkdir()
            (self.checkout / ".git").mkdir()
            return mock.Mock(returncode=0)
        with mock.patch("cloud.diagnostic_runner.subprocess.run", side_effect=mock_clone):
            clone_public_pilot(self.checkout)

    def test_git_error_never_exposes_stderr(self):
        with mock.patch("cloud.diagnostic_runner.subprocess.run", return_value=mock.Mock(returncode=1, stderr=b"SECRET")):
            with self.assertRaises(CloudPilotError) as caught:
                clone_public_pilot(self.checkout)
            self.assertNotIn("SECRET", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
