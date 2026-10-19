"""Mocked Hermes CLI contract; never touches actual login or paid inference."""
import json
import subprocess
import unittest
from unittest.mock import Mock

from cloud.hermes_smoke import read_only_smoke


class HermesCloudSmokeTests(unittest.TestCase):
    def setUp(self):
        self.config = {
            "model": {"provider": "openai-codex"},
            "fallback_providers": [],
            "auxiliary": {},
            "auth.adopt_external_logins": False,
        }
        self.usage = {"provider": "openai-codex", "source": "usage_api",
                      "plan": "Plus", "unavailable_reason": None}
        self.calls = []

    def simulate(self, *, config=None, usage=None, environment=None):
        values = self.config if config is None else config
        usage = self.usage if usage is None else usage

        def run(argv, **kwargs):
            self.calls.append(argv)
            self.assertFalse(kwargs["shell"])
            self.assertTrue(kwargs["capture_output"])
            if argv[1:3] == ["config", "get"]:
                key = argv[3]
                if key not in values:
                    return Mock(returncode=1, stdout="", stderr="secret")
                return Mock(returncode=0, stdout=json.dumps(values[key]), stderr="hidden")
            if argv[1:4] == ["usage", "--provider", "openai-codex"]:
                return Mock(returncode=0, stdout=json.dumps(usage), stderr="hidden")
            self.fail("unexpected command: " + str(argv))

        return read_only_smoke(
            environment={} if environment is None else environment,
            which=lambda _: "/usr/bin/hermes",
            invoke=run,
        )

    def test_success_only_verifies_usage_not_inference(self):
        result = self.simulate()
        self.assertEqual(result["status"], "subscription_usage_verified")
        self.assertFalse(result["inference_tested"])
        self.assertFalse(result["oauth_login_initiated"])
        self.assertEqual(result["provider"], "openai-codex")
        self.assertEqual(len(self.calls), 5)
        self.assertFalse(any("auth" in x[1:2] for x in self.calls))
        self.assertFalse(any("chat" in x[1:2] for x in self.calls))
        self.assertNotIn("Plus", json.dumps(result))

    def test_without_hermes_fails_closed(self):
        result = read_only_smoke(environment={}, which=lambda _: None,
                                 invoke=lambda *_a, **_k: self.fail("unexpected invocation"))
        self.assertEqual(result["status"], "hermes_not_installed")

    def test_paid_key_blocks_before_cli_runs(self):
        result = read_only_smoke(
            environment={"OPENAI_API_KEY": "TOP-SECRET-DO-NOT-LOG"},
            which=lambda _: self.fail("should not query binary"),
            invoke=lambda *_a, **_k: self.fail("should not invoke"),
        )
        self.assertEqual(result["status"], "paid_api_environment_present")
        self.assertNotIn("SECRET", json.dumps(result))

    def test_wrong_provider_never_queries_usage(self):
        cfg = dict(self.config, model={"provider": "openrouter"})
        result = self.simulate(config=cfg)
        self.assertEqual(result["status"], "subscription_provider_not_configured")
        self.assertEqual(len(self.calls), 1)

    def test_paid_fallback_never_queries_usage(self):
        cfg = dict(self.config, fallback_providers=["openrouter"])
        result = self.simulate(config=cfg)
        self.assertEqual(result["status"], "paid_fallback_not_excluded")
        self.assertFalse(any(x[1] == "usage" for x in self.calls))

    def test_external_login_adoption_must_be_disabled(self):
        cfg = dict(self.config, **{"auth.adopt_external_logins": True})
        result = self.simulate(config=cfg)
        self.assertEqual(result["status"], "external_login_adoption_not_disabled")

    def test_undecodable_usage_does_not_expose_output(self):
        def run(argv, **kwargs):
            if argv[1] == "config":
                return Mock(returncode=0, stdout=json.dumps(self.config[argv[3]]))
            return Mock(returncode=0, stdout="TOP-SECRET-INVALID-JSON")
        result = read_only_smoke(environment={}, which=lambda _: "hermes", invoke=run)
        self.assertEqual(result["status"], "usage_probe_unavailable")
        self.assertNotIn("SECRET", json.dumps(result))

    def test_unavailable_provider_does_not_claim_success(self):
        result = self.simulate(usage={"provider": "openai-codex", "unavailable_reason": "no_credential"})
        self.assertEqual(result["status"], "usage_probe_unavailable")

    def test_old_cli_without_usage_falls_back_to_auth_status(self):
        def run(argv, **kwargs):
            self.calls.append(argv)
            if argv[1:3] == ["config", "get"]:
                return Mock(returncode=0, stdout=json.dumps(self.config[argv[3]]))
            if argv[1] == "usage":
                return Mock(returncode=2, stdout="", stderr="invalid choice")
            if argv[1:4] == ["auth", "status", "openai-codex"]:
                return Mock(returncode=0, stdout="openai-codex: logged in\\n")
            self.fail(str(argv))
        result=read_only_smoke(environment={},which=lambda _: "/usr/bin/hermes",invoke=run)
        self.assertEqual(result["status"],"subscription_auth_status_verified")
        self.assertFalse(result["inference_tested"])
        self.assertEqual(self.calls[-1][1:],["auth","status","openai-codex"])

    def test_old_cli_cannot_claim_login_from_exit_code_only(self):
        def run(argv, **kwargs):
            if argv[1:3] == ["config", "get"]:
                return Mock(returncode=0, stdout=json.dumps(self.config[argv[3]]))
            if argv[1] == "usage":
                return Mock(returncode=2, stdout="", stderr="invalid choice")
            return Mock(returncode=0, stdout="openai-codex: not logged in\\n")
        result=read_only_smoke(environment={},which=lambda _: "/usr/bin/hermes",invoke=run)
        self.assertEqual(result["status"],"auth_status_probe_unavailable")

    def test_timeout_does_not_trigger_login_retry(self):
        def run(argv, **kwargs):
            if argv[1] == "config":
                return Mock(returncode=0, stdout=json.dumps(self.config[argv[3]]))
            raise subprocess.TimeoutExpired(argv, 30)
        result = read_only_smoke(environment={}, which=lambda _: "hermes", invoke=run)
        self.assertEqual(result["status"], "usage_probe_unavailable")
        self.assertFalse(result["oauth_login_initiated"])


if __name__ == "__main__":
    unittest.main()
