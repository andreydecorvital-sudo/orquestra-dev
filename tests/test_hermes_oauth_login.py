"""Hermes OAuth starter must use official CLI, never collect or leak tokens."""
import subprocess
import unittest
from unittest import mock

from cloud.hermes_oauth_login import (
    LOGIN_ARGS, STATUS_ARGS, HermesLoginUnavailable, launch_hermes_device_login,
)


class HermesOAuthLoginTests(unittest.TestCase):
    def setUp(self):
        self.env={"HERMES_HOME":"/opt/orquestra/hermes"}
        self.which=lambda cmd: "/usr/local/bin/hermes" if cmd=="hermes" else None

    def test_never_initiate_without_explicit_operator_consent(self):
        with self.assertRaisesRegex(HermesLoginUnavailable,"awaiting_user_consent"):
            launch_hermes_device_login(consent=False,environment=self.env,which=self.which)

    def test_never_initiate_from_untrusted_headless_context(self):
        with self.assertRaisesRegex(HermesLoginUnavailable,"trusted_terminal_required"):
            launch_hermes_device_login(consent=True,interactive=False,environment=self.env,which=self.which)

    def test_missing_runtime_is_reported(self):
        with self.assertRaisesRegex(HermesLoginUnavailable,"hermes_not_installed"):
            launch_hermes_device_login(consent=True,environment=self.env,which=lambda _:None)

    def test_paid_keys_prohibit_auth(self):
        for key in ("OPENAI_API_KEY","OPENROUTER_API_KEY","ANTHROPIC_API_KEY"):
            with self.subTest(key=key), self.assertRaisesRegex(HermesLoginUnavailable,"paid_provider_environment_blocked"):
                launch_hermes_device_login(consent=True,environment={**self.env,key:"secret"},which=self.which)

    def test_runs_official_hermes_cli_only_no_shell_no_token_capture(self):
        calls=[]
        def run(cmd,**kw):
            calls.append((cmd,kw))
            return mock.Mock(returncode=0)
        result=launch_hermes_device_login(consent=True,environment=self.env,which=self.which,execute=run)
        self.assertEqual(result,"hermes_oauth_verified")
        self.assertEqual(calls[0][0],["/usr/local/bin/hermes",*LOGIN_ARGS])
        self.assertEqual(calls[1][0],["/usr/local/bin/hermes",*STATUS_ARGS])
        self.assertFalse(calls[0][1]["shell"])
        self.assertNotIn("capture_output",calls[0][1])
        self.assertFalse(calls[1][1]["shell"])
        self.assertTrue(calls[1][1]["capture_output"])
        self.assertLessEqual(calls[0][1]["timeout"],900)

    def test_login_failure_never_reports_cli_output(self):
        result=launch_hermes_device_login(
            consent=True,environment=self.env,which=self.which,
            execute=lambda *_a,**_kw:mock.Mock(returncode=1,stdout="SENSITIVE",stderr="TOKEN"))
        self.assertEqual(result,"device_login_failed")
        self.assertNotIn("SENSITIVE",result)

    def test_status_failure_does_not_claim_auth_success(self):
        run=mock.Mock(side_effect=[mock.Mock(returncode=0),mock.Mock(returncode=1)])
        result=launch_hermes_device_login(consent=True,environment=self.env,which=self.which,execute=run)
        self.assertEqual(result,"device_login_completed_status_unverified")

    def test_timeout_aborts(self):
        def throw(*_args,**_kwargs):
            raise subprocess.TimeoutExpired(cmd=["hermes"],timeout=900)
        with self.assertRaisesRegex(HermesLoginUnavailable,"device_login_unavailable"):
            launch_hermes_device_login(consent=True,environment=self.env,which=self.which,execute=throw)


if __name__=="__main__":
    unittest.main()
