# Orquestra API v2 — estabilidade, qualidade e autenticação oficial

A Orquestra possui uma API **própria** para a fila e os executores. Ela não
é uma API do chatgpt.com ou claude.ai, e não contorna limites de assinaturas.

## Contrato e segurança

- \`POST /functions/v1/orq-worker\`, ação \`register\`: exige JWT real da
  sessão Supabase e retorna um segredo aleatório para o dispositivo apenas
  uma vez.
- Ações \`capabilities\`, \`poll\`, \`heartbeat\`, \`complete\`:
  exigem \`X-Orq-Device-Id\` + \`X-Orq-Device-Secret\`. O servidor valida SHA-256
  e revogação antes de usar qualquer RPC privilegiada.
- \`GET /functions/v1/orq-worker/health\`: **liveness** sem credenciais, não
  prova que o banco está alcançável. Retorna \`api_version:2\`.
- Todas as respostas contêm \`x-orq-request-id\` para correlação segura.
  Logs nunca devem incluir tokens, prompts, cookies ou segredos.
- Após cada \`poll\`, o executor recebe \`attempt\` (número de 1 a 5).
  Esse número é **obrigatório** no \`heartbeat\` e \`complete\`. A RPC rejeita
  uma execução antiga que tentar confirmar uma tarefa retomada, ainda que
  a retomada ocorra no mesmo dispositivo.
- \`orq_nodes.secret_hash\` é legível somente por \`service_role\`. A interface
  autenticada recebe somente nome, identificador, última atividade e
  capacidades; RLS continua limitando o dono.
- O worker interrompe tentativas em \`401/403\` (precisa parear de novo) e
  respeita atraso maior para \`429\`.

## Ordem de publicação

1. Validar testes CI e diff no GitHub.
2. Aplicar SQL \`004_execution_fencing.sql\` no banco **exclusivo**
   \`kekxcvcgyexcbleifffq\`.
3. Publicar \`supabase/functions/orq-worker/index.ts\` com \`verify_jwt=false\`.
   É obrigatório porque aceita cabeçalhos de dispositivo; sua autenticação é
   implementada pela própria função.
4. Validar acesso por colunas, RLS, privilégios das RPCs e página de liveness.
5. Atualizar o executor Python antes de permitir novas missões de código.

Esta mudança é de **segurança e consistência** da Orquestra. Codex e Claude
Code ainda precisam estar instalados e autenticados pelas CLIs oficiais.
Não é legítimo copiar cookies do Chrome nem tratar o site oficial como
uma API de inferência ilimitada.

## Evidência de execução

Testes de contrato no GitHub validam o protocolo e as salvaguardas estáticas.
O teste real de tarefa \`codex\`/\`joint\` requer um executor autenticado.
**Não declarar sucesso ponta a ponta antes dele existir.**
