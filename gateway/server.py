"""Minimal localhost-only task gateway. Not a provider's inference API.

Does not read browser cookies or OAuth tokens. Requires an independent local
bearer token to submit tasks. Do NOT deploy this HTTP listener to Vercel.
"""
import hmac
import json
import os
import pathlib
import secrets
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from gateway.engine import GatewayError, execute_job, cli_status

HOST = "127.0.0.1"
DEFAULT_PORT = 3791
MAX_BODY = 12000


def build_handler(config, access_token, *, executor=execute_job):
    class Handler(BaseHTTPRequestHandler):
        server_version = "OrquestraLocal/0.9"
        def log_message(self, fmt, *args):
            pass  # No logging of payloads, authorization, or prompts.
        def respond(self, status, item):
            body = json.dumps(item, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        def authenticated(self):
            raw = self.headers.get("Authorization", "")
            expected = "Bearer " + access_token
            return hmac.compare_digest(raw, expected)
        def do_GET(self):
            if not self.authenticated():
                return self.respond(401, {"error": "unauthorized"})
            if self.path == "/v1/status":
                return self.respond(200, {"gateway": "online", "binding": "127.0.0.1", "billing": "subscription_only",
                                         "execution_enabled": bool(config.get("allow_execution")),
                                         "providers": {"codex": cli_status("codex"), "claude": cli_status("claude")}})
            self.respond(404, {"error": "not_found"})
        def do_POST(self):
            if not self.authenticated():
                return self.respond(401, {"error": "unauthorized"})
            if self.path != "/v1/tasks":
                return self.respond(404, {"error": "not_found"})
            try:
                length = int(self.headers.get("Content-Length", "-1"))
                if length < 2 or length > MAX_BODY:
                    return self.respond(413, {"error": "invalid_payload_size"})
                payload = json.loads(self.rfile.read(length))
                result = executor(config, payload)
                return self.respond(200, result)
            except (json.JSONDecodeError, ValueError, TypeError):
                return self.respond(400, {"error": "invalid_json"})
            except GatewayError as ex:
                return self.respond(409, {"error": "task_blocked", "reason": str(ex)[:360]})
            except Exception:
                return self.respond(500, {"error": "internal_error"})
    return Handler


def main():
    path = pathlib.Path(os.environ.get("ORQ_GATEWAY_CONFIG", pathlib.Path(__file__).parent / "config.json"))
    if not path.exists():
        sys.exit("Copie gateway/config.example.json para gateway/config.json e configure o projeto permitido")
    config = json.loads(path.read_text(encoding="utf-8"))
    secret = os.environ.get("ORQ_LOCAL_TOKEN", "")
    if len(secret) < 32:
        sys.exit("Defina ORQ_LOCAL_TOKEN com 32+ caracteres aleatórios; NÃO envie ao site ou ao GitHub")
    port = int(os.environ.get("ORQ_GATEWAY_PORT", str(DEFAULT_PORT)))
    if not 1024 <= port <= 65535:
        sys.exit("Porta inválida")
    server = ThreadingHTTPServer((HOST, port), build_handler(config, secret))
    print("Orquestra Gateway na máquina local 127.0.0.1:" + str(port) + " | subscription-only")
    print("NÃO expõe API externa e não aceita API keys pagas. CTRL+C para parar")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Encerrando...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
