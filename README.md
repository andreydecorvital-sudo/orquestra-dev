# Orquestra Dev v1.0 — conectores e fila durável

**Produto independente** para tarefas de desenvolvimento coordenadas com identidades Lelouch/Nagi e uso de Codex + Claude Code **por login da assinatura**, não por API keys pagas desses provedores. A interface é simples, preta/branca/vermelha. Hermes ficará como executor/coordenador opcional de procedimentos, mas **não há integração real de Hermes nesta versão**.

## O que existe AGORA, sem marketing

| Recurso | Código | Remoto em produção |
|---|---|---|
| UI conectável (`web-live/`) | ✅ | **Publicada** em https://orquestra-dev-app.vercel.app/ · aguardando banco exclusivo |
| Login próprio via Supabase Auth | ✅ | Pendente projeto Supabase dedicado e conta de login |
| Projetos com RLS, fila e logs (`sql/`) | ✅ | Migrações não aplicadas em banco remoto |
| Leases 8min / heartbeat / reatribuição / máximo 3 tentativas | ✅ | Pendente deploy de Edge Function |
| Runner Python outbound HTTPS (`runner/agent_worker.py`) | ✅ | Pendente instalação e pareamento manual no dispositivo |
| Codex / Claude via CLIs oficiais | ✅ Adaptadores locais | Sessões reais ainda não autenticadas/testadas |
| Hermes, execução na nuvem sem PC, publicação automática | Não | **Não ativados** |
| Vercel `orquestra-dev-app.vercel.app` | ✅ GitHub conectado | **v1.0 publicada**; versão anterior permanece em `orquestra-dev.vercel.app` |
| GitHub `andreydecorvital-sudo/orquestra-dev` | ✅ 44 arquivos versionados | CI automático aprovado; repositório público |

**Nunca assumir execução 24/7** com notebook desligado. A fila persiste, mas os jobs dependem de um executor real ligado na nuvem ou em máquina local. Assinaturas continuam sujeitas às quotas e termos dos seus provedores.

## Fluxo pretendido

```text
Interface Vercel (login Supabase Auth)
   └── cria orq_tasks em projeto próprio (RLS por usuário)
       └── Edge Function autentica worker por segredo de dispositivo
           └── RPC PostgreSQL faz claim atômico (SKIP LOCKED)
               └── runner Python anuncia capacidades oficiais autenticadas
                   ├── Codex (ChatGPT login) → código
                   ├── Claude Code (login Claude) → plano/design/revisão
                   ├── Joint → Claude planeja; Codex implementa; Claude revisa
                   └── Diagnose / integrations → sem modelos
               └── salva patch Git local; heartbeat; finaliza no banco
```

**Segurança**: produção Argoplace/CRM nunca é alterada automaticamente. Repositórios autorizados localmente; modelo não recebe token GitHub, tokens fiscais, service role ou cookie de navegador. Patches e relatórios são revisados antes de PR ou deploy. A fila de jobs executa somente tipos de tarefa pré-definidos; não aceita comandos shell arbitrários.

## Como conectar em ordem

1. **GitHub**: `andreydecorvital-sudo/orquestra-dev` está criado e a fonte está versionada. **Atenção:** o repositório está público; configure `private` no GitHub antes de armazenar detalhes corporativos. Mantenha `main` protegido e exija revisão para produção.
2. **Supabase**: confirmar a organização (há `andreydecorvital-sudo's Org`) e os eventuais custos **antes** da criação. Usar projeto EXCLUSIVO `orquestra-dev` na região `sa-east-1`. Nunca criar tabelas no banco do Argoplace, CRM, botlab ou affiliate-machine.
3. **SQL**: aplicar, nesta ordem, `sql/001_init.sql`, `sql/002_integrations.sql`, `sql/003_durable_execution.sql` em projeto próprio. Verificar permissões e teste RLS usuário A/B. Políticas públicas: `anon` não lê tabelas de negócio; usuário vê só seu próprio conteúdo; Edge Function usa `service_role` privado.
4. **Auth**: desativar inscrição pública no Supabase Auth e criar apenas usuários convidados. Configure domínio e URL de redirecionamento do site da Orquestra.
5. **Edge Function**: publicar `supabase/functions/orq-worker/index.ts` com `verify_jwt=false`; ela valida JWT humano na ação `register` e o segredo do nó em `poll`, `heartbeat`, `capabilities`, `complete`. Defina `ORQ_ALLOWED_ORIGIN=https://orquestra-dev-app.vercel.app` e mantenha `SUPABASE_SERVICE_ROLE_KEY` apenas como segredo de servidor.
6. **UI**: está publicada em `https://orquestra-dev-app.vercel.app` a partir de `web-live/` neste GitHub. Pushes para `main` acionam Vercel automaticamente. O usuário informa apenas a URL e a chave pública `sb_publishable_...` em **Configurar** e faz login na conta privada.
7. **Executor**: copiar `runner/agent-worker.example.json` para `runner/agent-worker.json`. No painel, cadastre projeto e pareie executor, depois configure `node_id`, `node_secret` e allowlist da pasta Git para cada project_id. Instale CLIs e faça `codex login` e `claude` com login oficial. Verifique `codex login status` e `claude auth status`. Ative `allow_execution` somente depois de uma missão diagnóstica validada.
8. **Piloto**: usar um repositório de testes sem segredos. Executar `diagnose` (sem IA), depois `codex`, `claude`, `joint`. Confirmar conclusão/erro, logs, patch no runner, lease e reexecução após interrupção. Só depois conectar repositórios privados de produção, sempre sem auto-deploy.

## Rodar o painel local

```bash
cd web-live
python -m http.server 3333
```

Acesse http://localhost:3333. Sem projeto Supabase, aparecerá **Configurar**, não uma fila falsa.

## Executar o worker (na máquina que pode ficar ligada)

```bash
# Linux/macOS/Windows Powershell com Python
python -m runner.agent_worker
```

O arquivo local `runner/agent-worker.json` deve estar presente (ignorado no Git). Use o exemplo. O worker faz apenas conexões HTTPS **de saída**, sem abrir servidor no notebook. Quando o login de uma CLI não está pronto, ele não anuncia capacidade para receber tarefas daquele modelo. O gateway HTTP local anterior (`gateway/server.py`) continua opcional e **nunca** deve ser publicado na internet.

## Testes

```bash
python -m unittest discover -s tests -v
python -m compileall -q gateway runner orchestration
node --check web-live/app.js
```

**v1.0 passou nos testes de código locais, mas não foi testado com um projeto Supabase real nem com logins reais de Codex/Claude.** O teste de PostgreSQL/RLS/Edge Function só pode ser feito após a criação do banco. Não afirmar 24/7 ativo antes de pilotar com worker remoto.

## Decisões vinculantes

Leia `policies/SUBSCRIPTION_ONLY.md`. Não criar `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` pagos como fallback. HTTP local da Orquestra **não equivale** a disponibilizar uma API de inferência do fornecedor nem contorna limite de assinatura. Não extrair cookies nem automatizar interfaces protegidas de chat por fora das CLIs oficiais.
