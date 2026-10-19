"""Non-interactive, read-only Hermes ChatGPT/Codex subscription readiness check.

No OAuth login flow or inference is started. This reads only provider config
and, after policy checks, usage status from the official Hermes CLI.
All upstream stdout/stderr and credentials are discarded in the report.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from collections.abc import Callable, Mapping
from typing import Any

# Never proceed while a paid provider API key is supplied to this process.
FORBIDDEN_KEYS = frozenset({
    "OPENAI_API_KEY", "CODEX_API_KEY", "ANTHROPIC_API_KEY",
    "OPENROUTER_API_KEY", "NOUS_API_KEY", "XAI_API_KEY",
    "AI_GATEWAY_API_KEY", "ANTHROPIC_AUTH_TOKEN",
    "OPENAI_BASE_URL", "ANTHROPIC_BASE_URL",
})


def read_only_smoke(
    *,
    environment: Mapping[str, str] | None = None,
    which: Callable[[str], str | None] = shutil.which,
    invoke: Callable[..., Any] = subprocess.run,
) -> dict[str, Any]:
    """Return only fixed categorical values; never return raw CLI output.

    This does not authenticate Hermes or prove an inference works.
    """
    env = os.environ if environment is None else environment
    result: dict[str, Any] = {
        "provider": "openai-codex",
        "mode": "read_only",
        "status": "blocked",
        "oauth_login_initiated": False,
        "inference_tested": False,
        "tokens_exposed": False,
    }
    if any(env.get(key) for key in FORBIDDEN_KEYS):
        result["status"] = "paid_api_environment_present"
        return result
    exe = which("hermes")
    if not exe:
        result["status"] = "hermes_not_installed"
        return result

    def config(key: str) -> tuple[bool, Any]:
        try:
            p = invoke(
                [exe, "config", "get", key, "--json"],
                capture_output=True, text=True, timeout=18,
                shell=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return False, None
        if p.returncode != 0:
            return False, None
        try:
            return True, json.loads(p.stdout)
        except (TypeError, ValueError):
            return False, None

    ok, model = config("model")
    if not ok or not isinstance(model, dict) or model.get("provider") != "openai-codex" or model.get("api_key") or model.get("base_url"):
        result["status"] = "subscription_provider_not_configured"
        return result

    for key in ("fallback_providers", "auxiliary"):
        ok, setting = config(key)
        if not ok or setting not in (None, [], {}):
            result["status"] = "paid_fallback_not_excluded"
            return result

    ok, adopted = config("auth.adopt_external_logins")
    if not ok or adopted is not False:
        result["status"] = "external_login_adoption_not_disabled"
        return result

    try:
        p = invoke(
            [exe, "usage", "--provider", "openai-codex", "--json"],
            capture_output=True, text=True, timeout=30,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        result["status"] = "usage_probe_unavailable"
        return result
    if p.returncode != 0:
        # v0.21.3 (2026.9.14) predates "hermes usage". Use the
        # supported, read-only auth status command as a *weaker* signal.
        # Exit code 0 alone is insufficient: auth status may print
        # "not logged in" and still exit cleanly.
        try:
            auth = invoke(
                [exe, "auth", "status", "openai-codex"],
                capture_output=True, text=True, timeout=30,
                shell=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            result["status"] = "auth_status_probe_unavailable"
            return result
        auth_text = auth.stdout if isinstance(auth.stdout, str) else ""
        result["status"] = (
            "subscription_auth_status_verified"
            if auth.returncode == 0 and
                re.search(r"(?im)^\s*openai-codex\s*:\s*logged\s+in\s*$", auth_text)
            else "auth_status_probe_unavailable"
        )
        return result
    try:
        usage = json.loads(p.stdout)
    except (TypeError, ValueError):
        result["status"] = "usage_probe_unavailable"
        return result
    if (not isinstance(usage, dict) or usage.get("provider") != "openai-codex"
            or usage.get("unavailable_reason")):
        result["status"] = "usage_probe_unavailable"
        return result
    result["status"] = "subscription_usage_verified"
    return result


def main() -> int:
    print(json.dumps(read_only_smoke(), ensure_ascii=False, sort_keys=True))
    return 0  # A diagnostic status is an observation, not permission to run code.


if __name__ == "__main__":
    raise SystemExit(main())
