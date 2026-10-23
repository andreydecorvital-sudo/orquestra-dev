"""Read-only evidence before code: small local context, no model/API/build/deploy call.

Origin precision-engineering is the methodology. This module is an Orquestra
host adapter; candidate paths are hints, not validated root cause or ownership.
"""
from __future__ import annotations

import pathlib
import re
import subprocess
import unicodedata

from collections.abc import Sequence

_STOP = frozenset({
    "para", "como", "esse", "essa", "isso", "aqui", "agora", "pode", "preciso",
    "esta", "estao", "quero", "mais", "menos", "fazer", "fizemos", "codigo",
    "erro", "problema", "sistema", "quando", "porque", "onde", "antes",
    "with", "from", "this", "that", "have", "should", "need", "task", "please",
})
_LIMIT = 14
_MAX_TRACKED = 120000


class PrecisionError(RuntimeError):
    """Unable to establish trustworthy local repository context."""


def _git(worktree: pathlib.Path, *args: str) -> bytes:
    try:
        result = subprocess.run(
            ["git", *args], cwd=worktree, capture_output=True,
            timeout=20, check=False, shell=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PrecisionError("Nao foi possivel inspecionar o Git local") from exc
    if result.returncode:
        raise PrecisionError("Repositorio Git indisponivel para preflight")
    return result.stdout


def _fold(value: str) -> str:
    return "".join(
        char for char in unicodedata.normalize("NFKD", value.casefold())
        if not unicodedata.combining(char)
    )


def _terms(goal: str) -> set[str]:
    return {
        word for word in re.findall(r"[a-z0-9]{4,}", _fold(goal))
        if word not in _STOP
    }


def inspect_before_code(worktree: pathlib.Path, goal: str) -> dict[str, object]:
    """Read-only, deterministic paths/SHA; no file contents or secrets.

    Useful on a Codex-only path because it consumes no extra model quota.
    It intentionally DOES NOT call code valid or infer a root cause.
    """
    if not isinstance(goal, str) or not goal.strip():
        raise PrecisionError("Objetivo ausente")
    sha = _git(worktree, "rev-parse", "HEAD").decode("ascii", "replace").strip()
    if not re.fullmatch(r"[a-f0-9]{40}", sha):
        raise PrecisionError("SHA de base invalido")
    raw = _git(worktree, "ls-files", "-z")
    files = [p.decode("utf-8", "replace") for p in raw.split(b"\x00") if p]
    if len(files) > _MAX_TRACKED:
        raise PrecisionError("Repositorio excede o limite de inventario do preflight")
    words = _terms(goal)
    ranked: list[tuple[int, str]] = []
    for name in files:
        lower = _fold(name)
        scores = [term for term in words if term in lower]
        if scores:
            score = len(scores) + 2 * sum(term in pathlib.PurePosixPath(lower).name for term in scores)
            ranked.append((score, name))
    ranked.sort(key=lambda entry: (-entry[0], len(entry[1]), entry[1]))
    hints = [name for _, name in ranked[:_LIMIT]]
    instructions = [p for p in ("AGENTS.md", "CLAUDE.md", "GEMINI.md", "README.md")
                    if p in files]
    return {
        "base_sha": sha,
        "tracked_files": len(files),
        "candidate_paths": hints,
        "project_instructions": instructions,
        "confidence": "paths_only_not_root_cause",
        "extra_model_calls": 0,
    }


def precision_instructions(goal: str, context: dict[str, object]) -> str:
    """One provider call, with a mandatory research-first working method.

    Instructions do not constitute an executable proof that research happened;
    the post-patch verifier/reviewer is a separate, necessary gate.
    """
    if not re.fullmatch(r"[a-f0-9]{40}", str(context.get("base_sha", ""))):
        raise PrecisionError("Contexto sem commit de base confiavel")
    files: Sequence[str] = context.get("candidate_paths", [])  # type: ignore[assignment]
    docs: Sequence[str] = context.get("project_instructions", [])  # type: ignore[assignment]
    hints = "\n".join("- " + p for p in files) or "- Nenhum caminho sugerido; investigar a árvore local"
    guides = ", ".join(docs) or "instruções canônicas a identificar no projeto"
    return (
        "PROTOCOLO PRECISION ENGINEERING — SEM ETAPA EXTRA DE MODELO\n"
        "Base local: " + str(context["base_sha"]) + "\n"
        "Instrucoes do projeto a consultar: " + guides + "\n"
        "Candidatos encontrados apenas por nomes de arquivos (NAO sao prova da causa):\n"
        + hints + "\n\n"
        "1. ANTES DE CODAR, leia o owner real e as regras do projeto; pesquise implementacoes "
        "existentes e alteracoes concorrentes. Nunca trabalhe em uma rota legada por engano.\n"
        "2. Se for defeito, identifique reproducao, evidencias e causa raiz; cheque ao menos "
        "uma alternativa. Se nao puder comprovar a causa, NAO invente patch: devolva "
        "diagnostico/bloqueio com referencias.\n"
        "3. Estabeleca criterios verificaveis e um plano MINIMO por arquivo; escolha os testes "
        "antes da mudanca. Nao recrie core, provider ou abstracao paralela.\n"
        "4. Implemente apenas a mudanca necessaria. Para bug, tente registrar teste que "
        "falhe antes e passe depois; preserve permissao por empresa e efeitos externos.\n"
        "5. Execute verificacoes locais permitidas se disponiveis; nunca diga que um teste "
        "passou sem executa-lo. Nao dispare build Vercel Preview, deploy, push, merge, "
        "API paga, migracao, mensagem externa ou operacao fiscal.\n"
        "6. Nao faca mais que duas tentativas de reparo da mesma falha. Se persistir, "
        "pare, preserve o patch e retorne a investigacao.\n"
        "7. Ao encerrar, apresente causa/hipotese com evidencias, arquivos e testes executados "
        "ou ausentes, riscos e status real.\n"
        "8. QUALIDADE ANTES DE VELOCIDADE: para runtime, verifique caminhos ponta a ponta, "
        "resultado real, testes pertinentes no HEAD exato, revisao independente e rollback; "
        "para fiscal, seguranca, tenants, banco ou acoes externas, a falta de prova BLOQUEIA "
        "conclusao. Sintaxe verde nao prova funcionalidade. Nao afirme perfeicao nem "
        "resultado em producao sem observacao real. Sem prazo artificial para comecar ou "
        "aprovar PRs triviais; P0 validado tem prioridade.\n\n"
        "OBJETIVO DO USUARIO:\n" + goal
    )
