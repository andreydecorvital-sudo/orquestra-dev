"""Hermes API adapter for Orquestra's authorized LOCAL executor.

Hermes runs on the operator's machine; the Supabase/Vercel app never sees
API_SERVER_KEY. This is text-only planning, not an arbitrary remote shell.
Fail closed when Hermes advertises any enabled agent tools.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.request
from typing import Any

from gateway.engine import GatewayError

LOCAL_URL = "http://127.0.0.1:"
MAX_RESPONSE_BYTES = 131072
# Avoid accidental charges or machine side effects from Hermes tools.
# Restrict the API-server profile to *no enabled tools* for this bridge.
ALLOW_TOOLS: frozenset[str] = frozenset()

def api_key() -> str:
    """Read only the local Hermes API-server key. Never print or transmit remotely."""
    home = os.environ.get("HERMES_HOME")
    if home:
        directory = Path(home).expanduser()
    elif os.name == "nt":
        directory = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData/Local"))) / "hermes"
    else:
        directory = Path.home() / ".hermes"
    env_file = directory / ".env"
    if not env_file.is_file():
        raise GatewayError("Hermes não configurado: falta arquivo .env local")
    try:
        content = env_file.read_text(encoding="utf-8")
    except OSError as exc:
        raise GatewayError("Não foi possível ler a configuração local do Hermes") from exc
    values: dict[str, str] = {}
    for line in content.splitlines():
        m = re.match(r"^\s*(API_SERVER_KEY|API_SERVER_HOST|API_SERVER_PORT|API_SERVER_ENABLED)\s*=\s*(.*)$", line)
        if m:
            values[m.group(1)] = m.group(2).strip().strip("'\"")
    if values.get("API_SERVER_ENABLED", "").lower() != "true":
        raise GatewayError("Hermes API desativada; habilite localmente")
    if values.get("API_SERVER_HOST", "127.0.0.1") != "127.0.0.1":
        raise GatewayError("Hermes deve escutar exclusivamente em 127.0.0.1")
    if values.get("API_SERVER_PORT", "8642") != "8642":
        raise GatewayError("Hermes deve usar a porta local 8642 neste piloto")
    key = values.get("API_SERVER_KEY", "")
    if len(key) < 32 or len(key) > 2048 or "\r" in key or "\n" in key:
        raise GatewayError("API_SERVER_KEY inválida ou muito curta")
    return key

def _request(key: str, path: str, *, payload: dict[str, Any] | None = None,
             timeout: int = 4) -> Any:
    if path not in ("/v1/models", "/v1/toolsets", "/v1/chat/completions"):
        raise GatewayError("Endpoint Hermes fora da allowlist")
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        LOCAL_URL + "8642" + path,
        data=data,
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
        method="POST" if payload is not None else "GET",
    )
    # Fixed loopback target; no redirects to third-party hosts.
    opener = urllib.request.build_opener(_NoRedirects())
    try:
        with opener.open(req, timeout=timeout) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
            if len(raw) > MAX_RESPONSE_BYTES:
                raise GatewayError("Resposta Hermes excedeu limite de segurança")
            return json.loads(raw.decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # Never include raw upstream response: may contain secrets.
        if exc.code in (401, 403):
            raise GatewayError("Chave local Hermes não foi autorizada") from exc
        if exc.code == 429:
            raise GatewayError("Hermes/provedor atingiu limite de uso; tentar mais tarde") from exc
        raise GatewayError("Hermes indisponível HTTP " + str(exc.code)) from exc
    except (OSError, ValueError, UnicodeError) as exc:
        raise GatewayError("Não foi possível comunicar com o Hermes local") from exc

class _NoRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def safe_model(key: str) -> str:
    """Require safe tool configuration before any LLM request is made."""
    toolsets = _request(key, "/v1/toolsets")
    if not isinstance(toolsets, list):
        raise GatewayError("Hermes não expôs lista verificável de ferramentas")
    for bundle in toolsets:
        if not isinstance(bundle, dict) or not isinstance(bundle.get("enabled"), bool) \
                or not isinstance(bundle.get("tools"), list):
            raise GatewayError("Formato da lista de ferramentas não verificável")
        if bundle["enabled"]:
            for tool in bundle["tools"]:
                if not isinstance(tool, str) or tool not in ALLOW_TOOLS:
                    raise GatewayError("Hermes tem ferramentas ativas; desative-as para o perfil API")
    models = _request(key, "/v1/models")
    arr = models.get("data") if isinstance(models, dict) else None
    if not isinstance(arr, list) or len(arr) != 1 or not isinstance(arr[0], dict) \
            or not isinstance(arr[0].get("id"), str):
        raise GatewayError("Hermes não anunciou um modelo único e válido")
    name = arr[0]["id"]
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,100}", name):
        raise GatewayError("Nome de modelo Hermes inesperado")
    return name

def hermes_ready(config: dict[str, Any]) -> bool:
    if config.get("allow_execution") is not True or config.get("allow_hermes_planning") is not True:
        return False
    try:
        safe_model(api_key())
        return True
    except GatewayError:
        return False

def _redact(text: str) -> str:
    """Filter recognizable credential literals before publishing a short summary."""
    patterns = (
        r"sk-(?:proj-|ant-|or-)[A-Za-z0-9_-]{8,}",
        r"gh[pousr]_[A-Za-z0-9_]{8,}",
        r"github_pat_[A-Za-z0-9_]{8,}",
        r"sb_secret_[A-Za-z0-9_-]+",
        r"(?i)bearer\s+[A-Za-z0-9_.=-]{18,}",
    )
    for pat in patterns:
        text = re.sub(pat, "[SEGREDO REDIGIDO]", text)
    return text

def run_hermes(config: dict[str, Any], prompt: str, task_id: str) -> dict[str, Any]:
    """Text-only planning response. Does not grant Git or shell execution."""
    if config.get("allow_execution") is not True or config.get("allow_hermes_planning") is not True:
        raise GatewayError("Hermes necessita autorização explícita no executor local")
    if not isinstance(prompt, str) or not 8 <= len(prompt.strip()) <= 10000:
        raise GatewayError("Descrição Hermes inválida")
    if not re.fullmatch(r"[0-9a-fA-F-]{36}", task_id):
        raise GatewayError("Identificador de missão inválido")
    key = api_key()
    name = safe_model(key)
    message = (
        "Você é Hermes, revisor de software da Orquestra. Entregue apenas um plano "
        "com critérios de aceite, riscos, testes e próximos passos. Não declare "
        "que alterou arquivos ou executou comandos. Não solicite segredos nem "
        "ativações pagas. Não faça ações externas. Missão:\n\n" + prompt
    )
    response = _request(key, "/v1/chat/completions", payload={
        "model": name, "messages": [
            {"role": "system", "content": "Produza orientação técnica textual. Não use ferramentas."},
            {"role": "user", "content": message}
        ], "stream": False
    }, timeout=240)
    choices = response.get("choices") if isinstance(response, dict) else None
    content = (choices[0].get("message", {}).get("content")
               if isinstance(choices, list) and choices and isinstance(choices[0], dict) else None)
    if not isinstance(content, str) or not content.strip():
        raise GatewayError("Hermes não retornou resposta textual válida")
    return {"provider": "hermes", "output": _redact(content.strip())[:7000], "stages": [
        {"role": "hermes", "step": "plan"}
    ]}
