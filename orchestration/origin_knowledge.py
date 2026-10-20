"""Read-only, opt-in Origin repository knowledge adapter for Orquestra.

Origin is a *private GitHub repository*, not an AI model or executable agent.
The caller must present both an owner-scoped grant and a private GitHub token.
Never commit or pass Origin document bodies to the public Orquestra repository.
"""
from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from typing import Any

ORIGIN_REPOSITORY = "andreydecorvital-sudo/origin"
ORIGIN_REF = "main"
# Deliberately curated, not a recursive private-repository mirror.
ALLOWED_DOCUMENTS = frozenset({
    "START_HERE.md",
    "AGENTS.md",
    "catalog/extractions.json",
    "catalog/repositories.json",
    "docs/GOAL_LOOP_CONTRACT.md",
    "docs/LEARNING_LOG.md",
    "skills/repo-intelligence/SKILL.md",
    "skills/evidence-driven-loop/SKILL.md",
    "skills/self-improve/SKILL.md",
    "skills/human-centered-conversations/SKILL.md",
    "skills/reliable-async-jobs/SKILL.md",
    "skills/action-policy/SKILL.md",
    "skills/cross-repo-discovery/SKILL.md",
})
ROLE_DOCUMENTS: dict[str, tuple[str, ...]] = {
    "assistant": ("START_HERE.md", "AGENTS.md"),
    "research": ("skills/repo-intelligence/SKILL.md", "catalog/extractions.json"),
    "engineering": ("catalog/extractions.json", "skills/evidence-driven-loop/SKILL.md"),
    "design": ("skills/repo-intelligence/SKILL.md",),
    "marketing": ("skills/repo-intelligence/SKILL.md",),
    "commerce": ("catalog/extractions.json", "skills/action-policy/SKILL.md"),
    "review": ("skills/evidence-driven-loop/SKILL.md", "docs/LEARNING_LOG.md"),
}
MAX_RESPONSE_BYTES = 100_000
MAX_DOCUMENT_BYTES = 65_536
_SHA = re.compile(r"[0-9a-f]{40}", re.I)


class OriginUnavailable(RuntimeError):
    """Origin access/read denied or unavailable; do not silently assume an empty repo."""


@dataclass(frozen=True)
class OriginReadGrant:
    """Issued by trusted operator config, NEVER parsed from a user/LLM message."""
    owner_id: str
    repository: str
    allowed_paths: frozenset[str]
    read_only: bool = True


@dataclass(frozen=True)
class OriginDocument:
    repository: str
    path: str
    ref: str
    blob_sha: str
    content: str
    # Link is only an identity/provenance hint, never proof of public readability.
    source_url: str


@dataclass(frozen=True)
class OriginLearningProposal:
    """An evidence-backed suggestion; no write token, automation or merge."""
    title: str
    evidence: tuple[str, ...]
    learning: str
    target: str = "docs/LEARNING_LOG.md"
    status: str = "proposed"
    write_authorized: bool = False


class _DenyRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req: Any, fp: Any, code: int,
                         msg: str, headers: Any, newurl: str) -> None:
        return None


def _default_fetch(request: urllib.request.Request, timeout: float) -> bytes:
    opener = urllib.request.build_opener(_DenyRedirects())
    with opener.open(request, timeout=timeout) as response:
        raw = response.read(MAX_RESPONSE_BYTES + 1)
    return raw


def read_origin_document(
    *,
    path: str,
    owner_id: str,
    grant: OriginReadGrant,
    github_token: str,
    fetch: Callable[[urllib.request.Request, float], bytes] = _default_fetch,
) -> OriginDocument:
    """Read one allowlisted private file using a permission checked runtime token.

    No scanning private source files, no implicit GitHub credentials, no network
    redirects, no secret logged or returned, no arbitrary repository URLs.
    """
    if not isinstance(grant, OriginReadGrant) or not isinstance(owner_id, str):
        raise OriginUnavailable("Permissão Origin ausente")
    if not owner_id or owner_id != grant.owner_id or not grant.read_only:
        raise OriginUnavailable("Origin não autorizado para este proprietário")
    if grant.repository != ORIGIN_REPOSITORY or path not in ALLOWED_DOCUMENTS \
            or path not in grant.allowed_paths:
        raise OriginUnavailable("Arquivo Origin fora do escopo autorizado")
    if not isinstance(github_token, str) or len(github_token) < 16 \
            or any(ch.isspace() for ch in github_token):
        raise OriginUnavailable("Credencial GitHub privada não configurada")

    encoded_path = "/".join(urllib.parse.quote(p, safe="") for p in path.split("/"))
    url = (f"https://api.github.com/repos/{ORIGIN_REPOSITORY}/contents/"
           f"{encoded_path}?ref={ORIGIN_REF}")
    request = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "Authorization": "Bearer " + github_token,
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "Orquestra-Origin-Reader",
    }, method="GET")
    try:
        raw = fetch(request, 12.0)
    except (urllib.error.HTTPError, urllib.error.URLError, OSError, TimeoutError) as exc:
        # No upstream body, request headers or token included in error messages.
        raise OriginUnavailable("Origin inacessível à credencial autorizada") from None
    if not isinstance(raw, bytes) or len(raw) > MAX_RESPONSE_BYTES:
        raise OriginUnavailable("Resposta Origin inválida ou excede limite")
    try:
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict) or payload.get("type") != "file" \
                or payload.get("path") != path or payload.get("encoding") != "base64" \
                or not isinstance(payload.get("content"), str):
            raise ValueError("Invalid GitHub response")
        sha = payload.get("sha")
        if not isinstance(sha, str) or not _SHA.fullmatch(sha):
            raise ValueError("Invalid sha")
        body = base64.b64decode(payload["content"], validate=False)
        if len(body) > MAX_DOCUMENT_BYTES:
            raise ValueError("File too large")
        content = body.decode("utf-8")
    except (ValueError, TypeError, KeyError, UnicodeError, binascii.Error):
        raise OriginUnavailable("Documento Origin inválido ou excede limite") from None
    return OriginDocument(
        repository=ORIGIN_REPOSITORY, path=path, ref=ORIGIN_REF,
        blob_sha=sha, content=content,
        source_url=f"https://github.com/{ORIGIN_REPOSITORY}/blob/{ORIGIN_REF}/{path}",
    )


def recommended_origin_paths(role: str) -> tuple[str, ...]:
    """Origin canonical rules first, then relevant skill; not proof of access."""
    if role not in ROLE_DOCUMENTS:
        return ()
    return tuple(dict.fromkeys(
        ("START_HERE.md", "AGENTS.md", *ROLE_DOCUMENTS[role])
    ))


def load_origin_context(
    *,
    role: str,
    owner_id: str,
    grant: OriginReadGrant,
    github_token: str,
    max_documents: int = 4,
    fetch: Callable[[urllib.request.Request, float], bytes] = _default_fetch,
) -> tuple[OriginDocument, ...]:
    """Retrieve small, owner-scoped context with immutable source provenance.

    The caller must not persist document bodies to Orquestra's public repo,
    logs, analytics or another tenant's conversation. No caching by default.
    """
    if isinstance(max_documents, bool) or not isinstance(max_documents, int) \
            or not 1 <= max_documents <= 4:
        raise OriginUnavailable("Limite de documentos Origin inválido")
    paths = recommended_origin_paths(role)
    if not paths:
        raise OriginUnavailable("Especialidade Origin desconhecida")
    return tuple(
        read_origin_document(
            path=path, owner_id=owner_id, grant=grant,
            github_token=github_token, fetch=fetch,
        )
        for path in paths[:max_documents]
    )


def propose_origin_learning(*, title: str, learning: str,
                            evidence: tuple[str, ...], verified: bool
                            ) -> OriginLearningProposal:
    """Prepare a PRIVATE review candidate only after trusted verification.

    Never commits, invokes the GitHub API or changes Origin automatically.
    """
    if not verified or not isinstance(evidence, tuple) or not evidence \
            or any(not isinstance(v, str) or not v.strip() for v in evidence):
        raise ValueError("Aprendizado exige evidências verificadas")
    if not isinstance(title, str) or not (4 <= len(title.strip()) <= 140) \
            or not isinstance(learning, str) or not (12 <= len(learning.strip()) <= 4000):
        raise ValueError("Aprendizado inválido")
    return OriginLearningProposal(
        title=title.strip(), learning=learning.strip(),
        evidence=tuple(v.strip() for v in evidence),
    )
