"""Cloud-first diagnostic-only worker. Never executes Codex, Claude or Hermes.

Uses only a hardcoded public sandbox repository and scoped, in-memory device
credentials from the cloud secret store. It does not access Argoplace data.
"""
from __future__ import annotations

import os
import pathlib
import re
import subprocess
import tempfile
from typing import Mapping

PUBLIC_PILOT_REPO = "https://github.com/andreydecorvital-sudo/orquestra-dev.git"
UUID_RE = re.compile(r"[0-9a-fA-F-]{36}\Z")
SECRET_RE = re.compile(r"[0-9a-fA-F]{64}\Z")
SUPABASE_URL_RE = re.compile(r"https://[a-z0-9-]+\.supabase\.co\Z", re.IGNORECASE)


class CloudPilotError(RuntimeError):
    """A deliberately redacted and actionable pilot failure."""


def config_from_environment(env: Mapping[str, str], checkout: pathlib.Path) -> dict:
    url = env.get("ORQ_CLOUD_SUPABASE_URL", "").rstrip("/")
    node_id = env.get("ORQ_CLOUD_NODE_ID", "")
    node_secret = env.get("ORQ_CLOUD_NODE_SECRET", "")
    project_id = env.get("ORQ_CLOUD_PROJECT_ID", "")
    if not SUPABASE_URL_RE.fullmatch(url):
        raise CloudPilotError("URL do Supabase dedicado ausente ou inválida")
    if not UUID_RE.fullmatch(node_id) or not UUID_RE.fullmatch(project_id):
        raise CloudPilotError("IDs do nó/projeto devem ser UUIDs válidos")
    if not SECRET_RE.fullmatch(node_secret):
        raise CloudPilotError("Segredo do dispositivo no formato inválido")
    if env.get("ORQ_CLOUD_ENABLE_CODE", "").lower() in {"1", "true", "yes"}:
        raise CloudPilotError("Execução de IA não é permitida neste piloto")
    if env.get("ORQ_CLOUD_PILOT_REPOSITORY", PUBLIC_PILOT_REPO) != PUBLIC_PILOT_REPO:
        raise CloudPilotError("Piloto restrito ao repositório público da Orquestra")
    return {
        "supabase_url": url,
        "node_id": node_id,
        "node_secret": node_secret,
        "projects": {project_id: {"slug": "orquestra_pilot", "path": str(checkout)}},
        "allow_execution": False,
        "allow_hermes_planning": False,
        "poll_seconds": 25,
    }


def clone_public_pilot(checkout: pathlib.Path) -> None:
    """Fetch exactly one allowlisted public GitHub repository, no credentials."""
    if checkout.exists():
        raise CloudPilotError("Workspace do piloto já existe")
    git_env = dict(os.environ)
    git_env["GIT_TERMINAL_PROMPT"] = "0"
    git_env["GIT_CONFIG_NOSYSTEM"] = "1"
    git_env["GIT_CONFIG_GLOBAL"] = os.devnull
    git_env["GIT_LFS_SKIP_SMUDGE"] = "1"
    try:
        result = subprocess.run(
            ["git", "clone", "--depth", "1", "--single-branch", "--branch", "main",
             "--", PUBLIC_PILOT_REPO, str(checkout)],
            capture_output=True, timeout=90, check=False, env=git_env,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CloudPilotError("Clone público não pôde ser concluído") from exc
    if result.returncode or not (checkout / ".git").exists():
        raise CloudPilotError("Repositório público do piloto indisponível")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="orq-cloud-diagnostic-") as temp:
        checkout = pathlib.Path(temp) / "pilot"
        try:
            config = config_from_environment(os.environ, checkout)
            clone_public_pilot(checkout)
        except CloudPilotError as exc:
            print("ORQUESTRA_CLOUD_PILOT_BLOCKED: " + str(exc), flush=True)
            return 1
        from runner.agent_worker import run_worker
        print("Orquestra Cloud: diagnóstico sem IA, Hermes e produção", flush=True)
        run_worker(config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
