"""Local subscription-authenticated coding engine.

Only invokes installed official Codex/Claude CLIs. Never calls paid model APIs
and never touches browser session cookies. No network-exposed listener here.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import secrets
import shutil
import subprocess
import tempfile
import threading
from typing import Any

from orchestration.quality import QualityError, inspect_worktree

API_ENV = {
    "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "CODEX_API_KEY",
    "ANTHROPIC_AUTH_TOKEN", "OPENAI_BASE_URL", "ANTHROPIC_BASE_URL",
    "CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX",
    "CLAUDE_CODE_USE_FOUNDRY", "AWS_BEARER_TOKEN_BEDROCK",
}
TASK_TYPES = {"code", "design", "review", "investigation"}
PROVIDERS = {"codex", "claude", "joint"}
_LOCK = threading.Lock()

class GatewayError(RuntimeError):
    pass


def clean_env(source: dict[str, str] | None = None) -> dict[str, str]:
    """Remove API credentials from spawned CLI subprocesses, fail if present in host."""
    source = dict(source if source is not None else os.environ)
    return {key: value for key, value in source.items() if key.upper() not in API_ENV}


def billing_keys_present(source: dict[str, str] | None = None) -> list[str]:
    env = source if source is not None else os.environ
    return sorted(key for key in env if key.upper() in API_ENV and env[key])


def clean_repo(repo: pathlib.Path) -> None:
    if not (repo / ".git").exists():
        raise GatewayError("Caminho autorizado precisa ser repositório Git")
    p = subprocess.run(["git", "status", "--porcelain"], cwd=repo,
                       capture_output=True, text=True, timeout=20, shell=False)
    if p.returncode or p.stdout.strip():
        raise GatewayError("O repositório principal deve estar limpo antes de iniciar uma missão")


def safe_projects(cfg: dict[str, Any]) -> dict[str, pathlib.Path]:
    projects = cfg.get("projects", {})
    if not isinstance(projects, dict) or not projects:
        raise GatewayError("Configure ao menos um projeto na allowlist local")
    result = {}
    for identifier, value in projects.items():
        if not re.fullmatch(r"[a-z][a-z0-9_-]{1,45}", identifier):
            raise GatewayError("ID do projeto inválido")
        path = pathlib.Path(value).expanduser().resolve(strict=True)
        if not path.is_dir() or not (path / ".git").exists():
            raise GatewayError("Projeto não é um repositório Git autorizado: " + identifier)
        result[identifier] = path
    return result


def cli_status(executable: str) -> dict[str, Any]:
    """Expose minimal diagnostic; never print user identity or credentials."""
    if executable not in {"codex", "claude"}:
        raise GatewayError("CLI desconhecida")
    if not shutil.which(executable):
        return {"installed": False, "login": "unavailable"}
    args = [executable, "login", "status"] if executable == "codex" else ["claude", "auth", "status"]
    try:
        p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=15, shell=False, env=clean_env())
        return {"installed": True, "login": "authenticated" if p.returncode == 0 else "not_authenticated"}
    except (OSError, subprocess.TimeoutExpired):
        return {"installed": True, "login": "unknown"}


def run_cli(provider: str, prompt: str, cwd: pathlib.Path, *, seconds: int = 240) -> dict[str, Any]:
    if provider not in {"codex", "claude"}:
        raise GatewayError("Provedor não autorizado")
    if not shutil.which(provider):
        raise GatewayError("CLI não instalado: " + provider)
    if provider == "codex":
        argv = ["codex", "exec", "--sandbox", "workspace-write", "-"]
        data = prompt
    else:
        argv = ["claude", "-p", "--permission-mode", "plan", "--output-format", "text", prompt]
        data = None
    try:
        p = subprocess.run(argv, cwd=str(cwd), input=data, capture_output=True,
                           text=True, encoding="utf-8", errors="replace",
                           shell=False, env=clean_env(), timeout=seconds)
    except subprocess.TimeoutExpired as exc:
        raise GatewayError(provider + " excedeu o tempo máximo de execução") from exc
    out = p.stdout[-14000:]
    if p.returncode != 0:
        # Do not echo raw stderr, which may contain user credentials or prompts.
        raise GatewayError(provider + " retornou código " + str(p.returncode) + "; consulte log local da CLI")
    return {"provider": provider, "ok": True, "output": out}


def validate_job(payload: dict[str, Any]) -> dict[str, str]:
    if not isinstance(payload, dict):
        raise GatewayError("A tarefa deve ser um objeto")
    name = payload.get("project", "")
    provider = payload.get("provider", "")
    task_type = payload.get("type", "code")
    prompt = payload.get("prompt", "")
    if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9_-]{1,45}", name):
        raise GatewayError("Projeto inválido")
    if provider not in PROVIDERS or task_type not in TASK_TYPES:
        raise GatewayError("Provedor ou tipo de tarefa não autorizado")
    if not isinstance(prompt, str) or not 8 <= len(prompt.strip()) <= 10000:
        raise GatewayError("Descrição deve conter entre 8 e 10000 caracteres")
    return {"project": name, "provider": provider, "type": task_type, "prompt": prompt.strip()}


def execute_job(cfg: dict[str, Any], payload: dict[str, Any], *, cli=run_cli) -> dict[str, Any]:
    job = validate_job(payload)
    projects = safe_projects(cfg)
    if job["project"] not in projects:
        raise GatewayError("Projeto não autorizado no runner")
    if not cfg.get("allow_execution", False):
        raise GatewayError("Execução desativada na configuração; autorize no runner local")
    if billing_keys_present():
        raise GatewayError("Variáveis de API pagas presentes no host; remova-as antes de executar: " + ", ".join(billing_keys_present()))
    if not _LOCK.acquire(blocking=False):
        raise GatewayError("Runner ocupado; apenas uma missão simultânea")
    worktree = None
    repo = projects[job["project"]]
    try:
        clean_repo(repo)
        with tempfile.TemporaryDirectory(prefix="orq-worktree-") as td:
            worktree = pathlib.Path(td) / "workspace"
            p = subprocess.run(["git", "worktree", "add", "--detach", str(worktree), "HEAD"],
                               cwd=str(repo), text=True, capture_output=True, shell=False, timeout=40)
            if p.returncode:
                raise GatewayError("Não foi possível preparar worktree isolado")
            # No automatic push/merge/deploy; detached worktree is preserved only as a patch.
            stages = []
            if job["provider"] in {"claude", "joint"}:
                plan = cli("claude", "Prepare um plano com critérios de aceite. NÃO altere arquivos.\n\n" + job["prompt"], worktree)
                stages.append({"role": "claude", "step": "plan", "result": plan["output"][-4000:]})
            if job["provider"] in {"codex", "joint"}:
                first = "Realize a tarefa apenas neste worktree. Não faça push, merge, deploy nem toque em credenciais.\n\n" + job["prompt"]
                if stages:
                    first += "\n\nPlanejamento inicial de Claude:\n" + stages[0]["result"]
                code = cli("codex", first, worktree)
                stages.append({"role": "codex", "step": "implement", "result": code["output"][-4000:]})
            # Include new files in the patch without staging their contents as commits.
            # Files larger than the response budget block delivery instead of being lost.
            intent = subprocess.run(["git", "add", "-N", "--", "."], cwd=str(worktree),
                                    capture_output=True, text=True, timeout=20, shell=False)
            if intent.returncode:
                raise GatewayError("Falha ao incluir novos arquivos no artefato de revisão")
            diff = subprocess.run(["git", "diff", "--binary", "HEAD"], cwd=str(worktree),
                                  capture_output=True, text=True, timeout=20, shell=False)
            if diff.returncode:
                raise GatewayError("Falha ao extrair as alterações do worktree")
            patch = diff.stdout
            patch_oversize = len(patch.encode("utf-8")) > 40000
            changed = subprocess.run(["git", "status", "--short"], cwd=str(worktree),
                                     capture_output=True, text=True, timeout=20, shell=False)
            if not patch.strip() and job["provider"] in {"codex", "joint"}:
                raise GatewayError("Execução terminou sem patch; nenhum resultado foi registrado como entregue")
            # No secrets should be returned as a patch; block suspicious credential literals.
            if re.search(r"(?:sk-(?:proj-|ant-)|gh[pousr]_|github_pat_|BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY)", patch, re.I):
                raise GatewayError("Patch aparenta conter credencial: revisão local obrigatória")
            # Durably preserve the patch before the temporary worktree is cleaned.
            # The path is owned by the local runner and never accepted from a remote task.
            local_artifacts = pathlib.Path.home() / ".orquestra" / "artifacts"
            local_artifacts.mkdir(mode=0o700, parents=True, exist_ok=True)
            artifact_id = secrets.token_hex(12)
            patch_path = local_artifacts / (artifact_id + ".patch")
            patch_path.write_text(patch, encoding="utf-8")
            try:
                patch_path.chmod(0o600)
            except OSError:
                pass
            # Preserve source changes BEFORE QA and Claude review: neither can erase work.
            try:
                quality = inspect_worktree(worktree)
            except QualityError as exc:
                raise GatewayError("Quality gate bloqueou entrega; patch local preservado: " + str(exc)) from exc
            if job["provider"] == "joint":
                review_prompt = ("Revise sem editar este trabalho em relação aos critérios. "
                                 "Aponte erros e melhorias. Não declare testes que não foram executados."
                                 "\n\nTarefa: " + job["prompt"] + "\n\nDiff:\n" + patch[:10000]
                                 + "\n\nQuality gate:\n" + json.dumps(quality, ensure_ascii=False))
                try:
                    review = cli("claude", review_prompt, worktree)
                except GatewayError as exc:
                    raise GatewayError("Revisão Claude indisponível; patch local preservado para nova revisão") from exc
                stages.append({"role": "claude", "step": "review", "result": review["output"][-4000:]})
            return {"status": "review_required", "project": job["project"], "mode": job["provider"],
                    "worktree_mode": "detached", "stages": stages, "quality": quality,
                    "changed_files": changed.stdout[:3000],
                    "patch": "" if patch_oversize else patch, "patch_oversize": patch_oversize,
                    "artifact_path": str(patch_path),
                    "note": "Patch salvo localmente para revisão. Nenhum push, PR, merge ou deploy foi feito."}
    finally:
        if worktree and worktree.exists():
            subprocess.run(["git", "worktree", "remove", "--force", str(worktree)],
                           cwd=str(repo), capture_output=True, timeout=25, shell=False)
        _LOCK.release()
