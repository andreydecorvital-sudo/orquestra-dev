#!/usr/bin/env python3
"""Orquestra Dev Lite: executor mínimo, somente biblioteca padrão Python.
Nunca executa shell proveniente da rede: tipos de tarefa são fechados e auditáveis.
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time
import re
import urllib.parse
import urllib.error
import urllib.request

BASE = pathlib.Path(__file__).resolve().parent
DEFAULT_CONFIG = BASE / 'config.json'


def load_config(path):
    with open(path, encoding='utf-8') as f:
        config = json.load(f)
    required = ('supabase_url', 'node_id', 'node_secret', 'projects')
    for name in required:
        if not config.get(name):
            raise ValueError('Configuração incompleta: ' + name)
    url = config['supabase_url'].rstrip('/')
    if not (url.startswith('https://') or url.startswith('http://localhost:')):
        raise ValueError('Endereço Supabase deve usar HTTPS')
    config['supabase_url'] = url
    return config


def request(config, payload, timeout=30):
    url = config['supabase_url'] + '/functions/v1/orq-worker'
    data = json.dumps(payload).encode('utf-8')
    headers = {
        'Content-Type': 'application/json',
        'X-Orq-Device-Id': config['node_id'],
        'X-Orq-Device-Secret': config['node_secret']
    }
    req = urllib.request.Request(url, data=data, headers=headers, method='POST')
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read(300000).decode('utf-8'))


def command(argv, cwd, timeout=20):
    proc = subprocess.run(argv, cwd=str(cwd), capture_output=True, text=True,
                          encoding='utf-8', errors='replace', timeout=timeout,
                          shell=False)
    return proc.returncode, (proc.stdout + '\n' + proc.stderr).strip()[:18000]


def project_directory(config, task):
    # O projeto é definido localmente pelo operador. O servidor não fornece caminhos.
    raw = config['projects'].get(task['project_id'])
    if not raw:
        raise RuntimeError('Projeto não autorizado neste notebook. Configure o ID no config.json')
    directory = pathlib.Path(raw).expanduser().resolve(strict=True)
    if not directory.is_dir():
        raise RuntimeError('Diretório do projeto inválido')
    if not (directory / '.git').exists():
        raise RuntimeError('Não é um repositório Git local')
    return directory


def diagnose(directory):
    if not shutil.which('git'):
        raise RuntimeError('Git não instalado')
    segments = []
    for args in (["git", "status", "--short", "--branch"],
                 ["git", "log", "-5", "--oneline"]):
        code, output = command(args, directory)
        segments.append('$ ' + ' '.join(args) + '\n' + output)
        if code and args[1] == 'log' and ('does not have any commits yet' in output or 'does not have any commits' in output):
            segments[-1] = '$ git log -5 --oneline\nRepositório ainda sem commits'
            continue
        if code:
            raise RuntimeError('\n'.join(segments))
    return '\n\n'.join(segments)


def safe_github_remote(remote):
    """Return a public repo label, never a URL with embedded credentials."""
    remote = remote.strip()
    if re.fullmatch(r'git@github\.com:[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:\.git)?', remote):
        return remote.removeprefix('git@github.com:').removesuffix('.git')
    try:
        url = urllib.parse.urlsplit(remote)
        if url.hostname and url.hostname.lower() == 'github.com' and url.scheme == 'https':
            path = url.path.strip('/').removesuffix('.git')
            if re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', path):
                return path
    except ValueError:
        pass
    return 'Origem externa ou não reconhecida (endereço ocultado)'


def argo_print_status(program_data=None, program_files=None, is_windows=None):
    """Only installation/service indicators. Never reads pairing tokens, jobs or labels."""
    if is_windows is None:
        is_windows = os.name == 'nt'
    if not is_windows:
        return 'Argoplace Print: diagnóstico do serviço disponível apenas no Windows.'
    root = pathlib.Path(program_data or os.environ.get('PROGRAMDATA', r'C:\ProgramData')) / 'ARGO' / 'Print'
    exe = pathlib.Path(program_files or os.environ.get('ProgramFiles', r'C:\Program Files')) / 'ARGO' / 'Print'
    installed = (exe / 'Agent' / 'ARGO.Print.Agent.exe').is_file()
    paired_state_present = (root / 'agent-state.json').is_file()
    try:
        code, output = command(['sc.exe', 'query', 'ARGO Print Agent'], pathlib.Path.cwd(), timeout=8)
        if code != 0:
            service_state = 'não registrado ou sem permissão de consulta'
        elif re.search(r'\bRUNNING\b', output):
            service_state = 'em execução'
        elif re.search(r'\bSTOPPED\b', output):
            service_state = 'parado'
        else:
            service_state = 'estado não identificado'
    except (OSError, subprocess.TimeoutExpired):
        service_state = 'indisponível'
    return ('Argoplace Print (somente leitura):\n'
            + 'Instalação encontrada: ' + ('sim' if installed else 'não') + '\n'
            + 'Serviço Windows: ' + service_state + '\n'
            + 'Arquivo de estado local: ' + ('presente' if paired_state_present else 'não encontrado') + '\n'
            + 'Ações de impressão: desabilitadas no Orquestra Dev.')


def inspect_integrations(directory):
    """Repo discovery without retrieving business data or exposing credentials."""
    if not shutil.which('git'):
        raise RuntimeError('Git não instalado')
    code, origin = command(['git', 'remote', 'get-url', 'origin'], directory, timeout=8)
    repository = safe_github_remote(origin) if code == 0 else 'Nenhuma origem Git configurada'
    code, branch = command(['git', 'branch', '--show-current'], directory, timeout=8)
    branch = branch[:120] if code == 0 else 'indisponível'
    checks = {
        'Projeto Next.js': (directory / 'package.json').is_file(),
        'Supabase no código (configuração)': (directory / 'supabase' / 'config.toml').is_file(),
        'Supabase no código (migrations)': (directory / 'supabase' / 'migrations').is_dir(),
        'Argoplace Print Agent no código': (directory / 'tools' / 'argo-print-agent' / 'Program.cs').is_file(),
        'Argoplace Print Desktop no código': (directory / 'tools' / 'argo-print-desktop' / 'LocalStatus.cs').is_file(),
    }
    result = ['Diagnóstico de integrações — somente leitura',
              'GitHub (origem): ' + repository, 'Branch: ' + branch]
    result.extend(name + ': ' + ('encontrado' if exists else 'não encontrado') for name, exists in checks.items())
    result.append('Supabase remoto: não consultado — requer conector autorizado de leitura.')
    result.append(argo_print_status())
    return '\n'.join(result)


def execute_codex(config, directory, task):
    if config.get('enable_codex') is not True:
        raise RuntimeError('Codex desligado no config.json. Habilite após autenticar e revisar o projeto.')
    if not shutil.which('codex'):
        raise RuntimeError('Codex CLI não encontrado. Instale e faça login no terminal antes de ativar.')
    status_code, status = command(['git', 'status', '--porcelain'], directory)
    if status_code:
        raise RuntimeError('Git indisponível: ' + status)
    if status.strip():
        raise RuntimeError('Repositório possui alterações. Faça commit/stash antes de delegar.')
    branch = 'orq/' + task['id'][:12]
    code, out = command(['git', 'switch', '-c', branch], directory)
    if code:
        raise RuntimeError('Não foi possível criar branch isolado: ' + out)
    prompt = (
        'Você está trabalhando em um branch de desenvolvimento isolado. '
        'NÃO faça push, deploy, alterações de produção, emissão fiscal, envios a clientes ou publicação. '
        'Não leia nem revele segredos. Faça alterações somente neste repositório. '
        'Se uma etapa exigir credencial ou autorização, explique e pare. '
        'No final, informe modificações e testes realizados.\n\n'
        'Tarefa: ' + task['title'] + '\n' + task['instructions']
    )
    args = ['codex', 'exec', '--sandbox', 'workspace-write',
            '--ask-for-approval', 'never', '-']
    # Codex limita execução de comandos conforme políticas/sandbox da CLI.
    max_seconds = max(60, min(int(config.get('codex_timeout_seconds', 600)), 1800))
    try:
        proc = subprocess.run(args, input=prompt, cwd=str(directory), capture_output=True,
                              text=True, encoding='utf-8', errors='replace',
                              shell=False, timeout=max_seconds)
    except subprocess.TimeoutExpired:
        raise RuntimeError('Tempo limite do Codex atingido; verifique branch ' + branch)
    code2, changes = command(['git', 'status', '--short'], directory)
    if code2:
        changes = 'Indisponível'
    result = ('Branch: ' + branch + '\nStatus Codex: ' + str(proc.returncode) +
              '\nArquivos alterados:\n' + changes + '\n\nSaída:\n' +
              (proc.stdout + '\n' + proc.stderr)[-14000:])
    if proc.returncode:
        raise RuntimeError(result)
    return result


def execute(config, task):
    directory = project_directory(config, task)
    kind = task['kind']
    if kind == 'diagnose':
        return diagnose(directory)
    if kind == 'integrations':
        return inspect_integrations(directory)
    if kind == 'codex':
        return execute_codex(config, directory, task)
    raise RuntimeError('Tipo de tarefa não autorizado: ' + str(kind))


def main():
    config_path = pathlib.Path(os.environ.get('ORQ_CONFIG', str(DEFAULT_CONFIG)))
    config = load_config(config_path)
    pause = max(10, min(int(config.get('poll_seconds', 20)), 120))
    print('Orquestra Dev Lite | executor ativo | tarefas 1 por vez | CTRL+C para parar', flush=True)
    backoff = pause
    while True:
        try:
            data = request(config, {'action': 'poll'})
            backoff = pause
            task = data.get('task')
            if not task:
                time.sleep(pause)
                continue
            print('Tarefa: ' + task['title'] + ' (' + task['kind'] + ')', flush=True)
            try:
                output = execute(config, task)
                ok = True
            except Exception as e:
                output = type(e).__name__ + ': ' + str(e)
                ok = False
            request(config, {'action': 'complete', 'task_id': task['id'],
                             'ok': ok, 'output': output})
            print('Concluída' if ok else 'Falhou: '+output[:150], flush=True)
        except KeyboardInterrupt:
            print('\nExecução interrompida')
            break
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
            print('Conexão indisponível (' + type(e).__name__ + '); nova tentativa.', flush=True)
            time.sleep(backoff)
            backoff = min(backoff*2, 120)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError) as exc:
        print('ERRO: ' + str(exc), file=sys.stderr)
        sys.exit(1)
