"""Local, read-only readiness check for an Orquestra execution pilot.

Checks only device configuration, a mapping to a local Git directory, and
optional official CLI login status. Does not contact Supabase, invoke agents,
start a worker, or read project/source content. Never emits private values.
"""
from __future__ import annotations

import argparse
import json
import pathlib
from typing import Any, Callable

ROOT = pathlib.Path(__file__).resolve().parents[1]


def inspect_readiness(
    config_path: pathlib.Path,
    *,
    load_fn: Callable[[pathlib.Path], dict[str, Any]] | None = None,
    cli_fn: Callable[[str], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return only categorised evidence; do not include IDs, paths or secrets.

    A local-ready result is NOT an end-to-end pass: it cannot prove a remote
    queue, CLI quota, correct repo permissions or feature acceptance tests.
    """
    findings: dict[str, Any] = {
        "status": "blocked",
        "checks": {"config": "not_found", "repository": "not_checked",
                   "codex": "not_checked", "claude": "not_checked"},
        "mapped_repositories": 0,
        "end_to_end_verified": False,
        "backend": "not_checked",
        "tests": "not_run",
    }
    if not config_path.is_file():
        return findings
    if load_fn is None or cli_fn is None:
        # Import lazily to keep pure tests independent of runtime wiring.
        from runner.agent_worker import load_config, cli_status
        load_fn = load_fn or load_config
        cli_fn = cli_fn or cli_status
    try:
        config = load_fn(config_path)
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError):
        findings["checks"]["config"] = "invalid"
        return findings

    findings["checks"]["config"] = "valid"
    mappings = config.get("projects", {})
    if not isinstance(mappings, dict) or not mappings:
        findings["checks"]["repository"] = "missing_mapping"
        return findings

    findings["mapped_repositories"] = len(mappings)
    for value in mappings.values():
        if not isinstance(value, dict) or not isinstance(value.get("slug"), str) or not value["slug"].strip():
            findings["checks"]["repository"] = "invalid_mapping"
            return findings
        if not isinstance(value.get("path"), str) or not value["path"].strip():
            findings["checks"]["repository"] = "invalid_mapping"
            return findings
        try:
            local = pathlib.Path(value["path"]).expanduser().resolve(strict=True)
        except (ValueError, OSError, RuntimeError):
            findings["checks"]["repository"] = "unavailable"
            return findings
        # A .git directory or git worktree pointer is sufficient for this
        # shallow check; actual Git state is tested by the trusted gateway.
        if not local.is_dir() or not (local / ".git").exists():
            findings["checks"]["repository"] = "not_git_directory"
            return findings

    findings["checks"]["repository"] = "mapped_local_git"
    if config.get("allow_execution") is not True:
        findings["status"] = "diagnostics_ready_locally"
        return findings

    available = []
    for provider in ("codex", "claude"):
        try:
            value = cli_fn(provider)
            login = value.get("login") if isinstance(value, dict) else None
        except (OSError, ValueError, RuntimeError, TimeoutError):
            login = None
        findings["checks"][provider] = "authenticated" if login == "authenticated" else "not_authenticated_or_unavailable"
        if login == "authenticated":
            available.append(provider)
    findings["status"] = "code_ready_locally" if available else "login_required"
    findings["local_providers"] = available
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Diagnóstico local seguro da Orquestra")
    parser.add_argument("--config", type=pathlib.Path,
                        default=ROOT / "runner" / "agent-worker.json",
                        help="Caminho local do arquivo de pareamento (nunca publicado)")
    args = parser.parse_args(argv)
    evidence = inspect_readiness(args.config)
    print(json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True))
    # Nonzero code on incomplete preflight is useful for scripts and local CI;
    # diagnostic mode counts as a valid first-stage result.
    return 0 if evidence["status"] in {"diagnostics_ready_locally", "code_ready_locally"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
