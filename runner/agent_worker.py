"""Orquestra v1.0 durable worker, for an explicitly authorized Git repository.

Polls Supabase outbound over HTTPS. No port exposure, no paid AI APIs.
Codex/Claude execute only through gateway.engine via official login-based CLIs.
"""
from __future__ import annotations

import json
import os
import pathlib
import sys
import time
import threading
import urllib.error
import urllib.request
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gateway.engine import GatewayError, execute_job, cli_status  # noqa: E402


def load_config(path: pathlib.Path) -> dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8"))
    url = str(config.get("supabase_url", "")).rstrip("/")
    if not (url.startswith("https://") or url.startswith("http://localhost:")):
        raise ValueError("Supabase deve usar HTTPS")
    import re
    if not re.fullmatch(r"[0-9a-f-]{36}", str(config.get("node_id", "")), re.I):
        raise ValueError("node_id inválido")
    if not re.fullmatch(r"[0-9a-f]{64}", str(config.get("node_secret", "")), re.I):
        raise ValueError("node_secret inválido")
    config["supabase_url"] = url
    if not isinstance(config.get("projects"), dict):
        raise ValueError("Defina projects (ID remoto → slug local e pasta allowlisted)")
    if "allow_execution" not in config:
        config["allow_execution"] = False
    return config


def post(config:dict[str,Any],payload:dict[str,Any],timeout:int=35)->dict[str,Any]:
    url=config["supabase_url"]+"/functions/v1/orq-worker"
    data=json.dumps(payload,ensure_ascii=False).encode("utf-8")
    request=urllib.request.Request(url, data=data, headers={
        "Content-Type":"application/json",
        "X-Orq-Device-Id":str(config["node_id"]),
        "X-Orq-Device-Secret":str(config["node_secret"]),
    }, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read(512000).decode("utf-8"))


def work_once(config:dict[str,Any],task:dict[str,Any],send=post, engine=execute_job,
              heartbeat_interval:float=55)->dict[str,Any]:
    remote_id=str(task["project_id"])
    local=config["projects"].get(remote_id)
    if not isinstance(local, dict):
        raise GatewayError("Projeto remoto sem mapeamento autorizado no executor")
    slug=local.get("slug", "")
    directory=local.get("path", "")
    if not slug or not directory:
        raise GatewayError("Configure slug e path de projeto autorizado")
    kind=str(task.get("kind", ""))
    if kind not in {"codex","claude","joint","diagnose","integrations"}:
        raise GatewayError("Tipo não permitido")
    if kind in {"diagnose","integrations"}:
        # Existing read-only legacy diagnostics, no model session.
        from runner.worker import diagnose, inspect_integrations
        path=pathlib.Path(directory).expanduser().resolve(strict=True)
        if kind=="diagnose":
            return {"provider":"git","output":diagnose(path),"stages":[]}
        return {"provider":"git","output":inspect_integrations(path),"stages":[]}
    engine_cfg={"projects":{slug:directory},"allow_execution":config["allow_execution"]}
    title=str(task.get("title", ""))
    instructions=str(task.get("instructions", ""))
    prompt=title+"\n\n"+instructions
    stop=threading.Event()
    lease_lost=threading.Event()
    def pulse():
        while not stop.wait(heartbeat_interval):
            try:
                result=send(config,{"action":"heartbeat","task_id":task["id"]})
                if result.get("ok") is not True:
                    lease_lost.set();return
            except Exception:
                # Two missed beats may eventually expire lease; worker must not
                # claim success if persistence cannot be verified afterward.
                pass
    thread=threading.Thread(target=pulse,daemon=True)
    thread.start()
    try:
        result=engine(engine_cfg,{"project":slug,"provider":kind,"type":"code","prompt":prompt})
    finally:
        stop.set();thread.join(timeout=1)
    if lease_lost.is_set():
        raise GatewayError("Lease perdido durante execução. Patch local preservado; confira a fila")
    return result


def summarise(result:dict[str,Any])->str:
    """Keep remote evidence small. No output of local paths or raw secrets."""
    stages=result.get("stages",[])
    lines=["Execução finalizada; alterações permanecem no executor para revisão."]
    if result.get("provider") == "git":
        return str(result.get("output", ""))[:12000]
    lines.append("Agente: "+str(result.get("provider","unknown"))[:24])
    for step in stages:
        lines.append(str(step.get("step","stage"))+": "+str(step.get("role","agent")))
    if result.get("patch_saved") or result.get("artifact_path"):
        lines.append("Patch persistido no executor (não enviado integralmente ao backend)")
    lines.append("PR: não criado automaticamente; nenhuma ação em produção")
    return "\n".join(lines)[:18000]


def advertised_capabilities(config:dict[str,Any])->list[str]:
    caps=['diagnose','integrations']
    if config.get('allow_execution') is True:
        codex=cli_status('codex').get('login')=='authenticated'
        claude=cli_status('claude').get('login')=='authenticated'
        if codex: caps.append('codex')
        if claude: caps.append('claude')
        if codex and claude: caps.append('joint')
    return caps


def main()->None:
    path=pathlib.Path(os.environ.get("ORQ_AGENT_WORKER_CONFIG",ROOT/"runner"/"agent-worker.json"))
    if not path.is_file():
        raise SystemExit("Configure runner/agent-worker.json a partir do exemplo (não comitar)")
    config=load_config(path)
    interval=max(15,min(120,int(config.get("poll_seconds",25))))
    print("Orquestra v1.0: executor em outbound HTTPS, subscription only")
    next_capability_sync=0.0
    while True:
        try:
            if time.monotonic()>=next_capability_sync:
                post(config,{'action':'capabilities','capabilities':advertised_capabilities(config)})
                next_capability_sync=time.monotonic()+120
            data=post(config,{"action":"poll"})
            task=data.get("task")
            if not task:
                time.sleep(interval);continue
            print("MISSÃO",str(task.get("id",""))[:8],"tentativa",task.get("attempt"))
            try:
                result=work_once(config,task)
                ok=True;output=summarise(result)
            except Exception as e:
                ok=False;output="Missão falhou no executor: "+type(e).__name__+". Consulte logs locais."
            try:
                post(config,{"action":"complete","task_id":task["id"],"ok":ok,"output":output})
            except Exception:
                print("ERRO: não foi possível confirmar a conclusão. A fila recuperará o lease.")
        except KeyboardInterrupt:
            return
        except urllib.error.HTTPError as error:
            print("Backend indisponível HTTP",error.code)
            time.sleep(interval)
        except Exception as error:
            print("Backend indisponível:",type(error).__name__)
            time.sleep(interval)


if __name__=="__main__":
    main()
