# Hermes privado implantado na Railway — 2026-10-19

**Autorização:** titular aprovou exclusivamente deploy de um serviço Hermes isolado no projeto Railway `orquestra-cloud` e volume privado para OAuth. Não autorizou merge, mudança de CRM, mudanças Argoplace ou execução autônoma de missões.

## Implantação verificada

- Projeto Railway: `6f38abc3-4a78-4725-a55d-b2063019be11`
- Ambiente: `sandbox` (`4710cce6-c4c4-44e6-beca-7d732ea4074e`)
- Serviço: `orquestra-hermes-worker` (`00d8eb49-5294-4deb-98d4-68dce0588d21`), único no ambiente
- Fonte: Docker oficial `nousresearch/hermes-agent:v2026.9.14` (tag versionada; **digest imutável não confirmado**)
- Volume: `hermes-oauth-private`, 2048 MB, montado em `/opt/data`. O volume é exclusivo desse serviço.
- CPU: 1 vCPU; RAM: 2 GB; 1 réplica; processo inicial `sleep infinity`, sem missões e sem servidor de API público.
- Variáveis defensivas: `HERMES_HOME=/opt/data`, `HERMES_DASHBOARD=0`, `API_SERVER_ENABLED=false`.
- Publicação: `accept_deploy` confirmou a única alteração pendente do ambiente; deployment `7be58316-a766-4892-b3d0-3bd17cfc58f5`, `SUCCESS`, 1/1 réplicas online, zero falhas.
- `list_domains`/descrição do serviço: nenhum domínio; nenhum TCP proxy. Os workloads CRM, WAHA/Shopee e Supabase foram preservados.
- Sem OAuth realizado, sem credenciais OpenAI acessadas ou geradas, sem modelo ligado; despesas Railway pela instância viva podem começar agora.

## Login OAuth — não realizado

A integração Railway disponível neste chat oferece config/deploy/logs, **não exec/SSH privado interativo**. Por isso, não pode iniciar a CLI Hermes dentro do contêiner a partir deste chat, nem copiar o código de dispositivo de forma autenticada até a Orquestra.

O titular deve autenticar sua conta pessoal **somente pela página oficial gerada pela CLI do próprio Hermes**, usando o terminal privado do serviço. A Railway documenta `railway ssh`: https://docs.railway.com/cli/ssh.

Do terminal que tenha Railway CLI autenticado:

```sh
railway ssh -p 6f38abc3-4a78-4725-a55d-b2063019be11 -e sandbox -s 00d8eb49-5294-4deb-98d4-68dce0588d21
hermes auth add openai-codex --type oauth
```

**Não** colar código OAuth no GitHub, logs públicos, chat, Supabase ou Vercel. Confirmar no browser oficial. Depois, ainda no runtime, `hermes model` (ChatGPT or Codex Subscription), `hermes usage --provider openai-codex --json` e `python -m cloud.hermes_smoke` **somente se o módulo existir na imagem** (na imagem oficial a checagem custom não está instalada). O `cloud.hermes_oauth_login.py` no PR também não foi copiado automaticamente para a imagem Docker oficial.

O OAuth ainda **não** habilita missões na fila: o nó `orq_nodes` permanece sem pareamento. O link de UI na Vercel aponta à central de Hermes e mostra a dependência real, mas não inicia CLI remota.

## Segurança e custos

O serviço não está exposto. Não habilitar dashboard em `0.0.0.0`, compartilhamento de tokens, auth.json exportado, fallback pago ou ferramentas remotas sem revisão e autorização específicas. Depois do login, avaliar se a instância deve continuar 24/7: **1 vCPU/2GB em execução contínua consome recursos da Railway**.

Esta etapa não envolveu merge nem deploy de Argoplace, nem qualquer mutação no CRM.
