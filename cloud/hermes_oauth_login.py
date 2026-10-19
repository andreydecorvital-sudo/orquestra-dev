"""Launch the REAL Hermes device-code OAuth in the isolated Hermes runtime.

This module is not a browser impersonation and is intentionally not callable
from the public Vercel or Supabase Edge surfaces. It must run in the same
persistent machine/user profile that will subsequently execute Hermes.

No credentials, refresh tokens, callback URLs or CLI output are collected by
Orquestra. An authorized operator sees the Hermes CLI device challenge on
their trusted terminal and completes authorization at the official provider.

NO unattended OAuth, paid fallback, production Git/CRM access, or deployment.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from collections.abc import Callable, Mapping
from typing import Any

from cloud.hermes_smoke import FORBIDDEN_KEYS


class HermesLoginUnavailable(RuntimeError):
    """Categorical, secret-free error for missing runtime or consent."""


LOGIN_ARGS = ("auth", "add", "openai-codex", "--type", "oauth")
STATUS_ARGS = ("auth", "status", "openai-codex")


def launch_hermes_device_login(
    *,
    consent: bool,
    environment: Mapping[str, str] | None = None,
    which: Callable[[str], str | None] = shutil.which,
    execute: Callable[..., Any] = subprocess.run,
    interactive: bool = True,
) -> str:
    """Start the genuine Hermes CLI login and report only a categorical result.

    The CLI owns device-code generation, polling and token persistence. Never
    run this inside an HTTP handler or any ephemeral Vercel/Edge process.
    """
    if not consent:
        raise HermesLoginUnavailable("awaiting_user_consent")
    if not interactive:
        raise HermesLoginUnavailable("trusted_terminal_required")
    env = os.environ if environment is None else environment
    if any(env.get(key) for key in FORBIDDEN_KEYS):
        raise HermesLoginUnavailable("paid_provider_environment_blocked")
    binary = which("hermes")
    if not binary:
        raise HermesLoginUnavailable("hermes_not_installed")
    try:
        result = execute(
            [binary, *LOGIN_ARGS],
            shell=False,
            timeout=900,
            check=False,
            env=dict(env, NO_COLOR="1"),
        )
    except (OSError, subprocess.TimeoutExpired):
        raise HermesLoginUnavailable("device_login_unavailable") from None
    if result.returncode != 0:
        return "device_login_failed"
    try:
        verified = execute(
            [binary, *STATUS_ARGS],
            shell=False,
            timeout=30,
            check=False,
            capture_output=True,
            text=True,
            env=dict(env, NO_COLOR="1"),
        )
    except (OSError, subprocess.TimeoutExpired):
        return "device_login_completed_status_unverified"
    if verified.returncode != 0:
        return "device_login_completed_status_unverified"
    # Hermes v0.21.3 (2026.9.14) supports `auth status` but not
    # `hermes usage`. Exit code 0 alone does NOT prove a valid login.
    # Do not return the CLI output: it may contain account identifiers.
    safe_text = verified.stdout if isinstance(verified.stdout, str) else ""
    if re.search(r"(?im)^\\s*openai-codex\\s*:\\s*logged\\s+in\\s*$", safe_text):
        return "hermes_oauth_status_verified"
    return "device_login_completed_status_unverified"


def main(argv: list[str] | None = None) -> int:
    """Intentionally interactive. Never paste auth output in chat/CI/logs."""
    args = sys.argv[1:] if argv is None else argv
    if args != ["--user-approved"]:
        print("HERMES_LOGIN_BLOCKED: consent_required")
        return 2
    try:
        status = launch_hermes_device_login(
            consent=True,
            interactive=sys.stdin.isatty() and sys.stdout.isatty(),
        )
    except HermesLoginUnavailable as exc:
        print("HERMES_LOGIN_BLOCKED: " + str(exc))
        return 1
    print("HERMES_LOGIN_RESULT: " + status)
    return 0 if status == "hermes_oauth_status_verified" else 1


if __name__ == "__main__":
    raise SystemExit(main())
