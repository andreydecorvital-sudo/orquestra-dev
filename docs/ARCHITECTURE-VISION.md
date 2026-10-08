# Orquestra Dev — Architecture & destination (2026-10-08)

## Direção

* GPT/Codex: implementação, APIs, testes, bugs (responsável principal).
* Claude Code: UX/design e revisão de tarefas complexas.
* Ambos: arquitetura sensível, investigação ambígua, design+implementação, riscos altos.
* Agentes auxiliares: pesquisa de documentação, coleta de logs, contexto de `project-brain`, lint, CI, evidências.
* Lelouch/Nagi: identidades de equipe na UI; não são modelos de IA nem provedores.

## Mission lifecycle

`draft -> queued -> researching -> designing? -> implementing -> validating -> reviewing? -> awaiting_approval -> approved -> merged? -> deployed?`

Todo passo guarda: task_id, stage_id, project_id, provider, model/version, prompt/context hash, result URL/diff, logs sem segredos, start/end, retries, status, custo/uso quando disponível.

Estado futuro: `blocked_quota`, `blocked_auth`, `blocked_needs_human`, `failed`, `cancelled`.

SLA/24h se refere à **disponibilidade da fila e dos gatilhos**; não significa execução contínua gratuita, disponibilidade absoluta do modelo ou 24h de GPU ligada.

## Providers and runtimes

A. Codex Cloud, com autenticação e recursos oficiais, pode executar jobs na nuvem sem o PC local. Integração programática só quando autorizada para a conta ou via API com faturamento e quotas apropriados.

B. Claude Code Routines (research preview) aceitam GitHub event, schedule e authenticated API fire; guardam execuções na nuvem. Guardar tokens **somente** no backend da Orquestra, nunca no frontend.

C. Auxiliares sem modelo podem buscar documentação, resumir diffs, rodar verificações Git, compor contexto. Modelos de menor custo entram onde compensar, com autenticação e orçamento.

## Deployment architecture

- Site privado Vercel: painel da equipe, tarefas, histórico, approvals.
- Supabase dedicado: Auth + RLS, projetos, workspaces, fila durável/steps, audit/events, idempotency keys, job leases, retries e dead-letter.
- Execution adapters: Codex Cloud/CLI, Claude Routines, worker GitHub Actions ou serviço de execução remoto com egress control.
- GitHub: branch por tarefa, PR por mudança, checks obrigatórios antes de merge.
- Notebook de 2 GB: **opcional**, runner Python (rede outbound), nenhuma tarefa pesada ou modelo local obrigatório.
- Argoplace, CRM e outros projetos: acesso somente explicitamente concedido por workspace/projeto. Jamais partilhar service keys.

## Segurança (não negociar)

1. Identidade humana por workspace, papéis e projeto; RLS por dono.
2. Somente o executor tem credenciais de provedores; browser recebe zero segredos.
3. Tokens de GitHub/Claude e segredos Supabase ficam armazenados em secret manager específico da infraestrutura.
4. Somente repositórios allowlisted; worktree isolado / sandbox por tarefa.
5. Proibir prompt de usuário de sobrescrever políticas, permissão de deploy ou caminho de acesso a segredos.
6. Requerer aprovação humana para merge, deploy produção, qualquer operação fiscal, impressão, anúncios e envios a clientes.
7. Toda conclusão tem evidências: commit/PR, testes, logs, validação de aceite.
8. Limitar concorrência, créditos, falhas consecutivas e retentativas; não executar em loop infinito gastando limite.

## Milestones — critérios verificáveis

**M1 — Fila real:** 1 conta autenticada cria tarefa, ela é salva remotamente, reaparece em outro dispositivo, recebe ID estável e pode ser cancelada.

**M2 — Codex executa:** branch isolada, PR de teste, CI passa; retries e quotas visíveis. Nenhum deploy automático.

**M3 — Claude faz design:** especificação visual versionada, critérios de aceite, implementações feitas por GPT seguindo o design, revisão independente quando necessário.

**M4 — Cooperação real:** tarefa complexa percorre ambos os modelos, suporte e CI, com logs por etapa e gates; falhas são bloqueadas, não simuladas como concluídas.

**M5 — 24/7:** fila e gatilhos em nuvem, sem PC ligado, retries recuperáveis, alertas, limites e botão pausa total.

**M6 — Projetos de produção:** allowlist dos repositórios reais, pipelines de PR, auditoria, revisão e aprovação. Testar primeiro em repositório de laboratório.

## Módulo que já foi implementado

`orchestration/router.py` é um policy engine determinístico e testado que produz um plano de etapas. Não usa rede, credenciais, modelos, fila Supabase nem executa tarefas. Isso permite testar a política antes de conectar provedores reais.
