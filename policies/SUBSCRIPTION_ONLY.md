# REGRA INEGOCIÁVEL — SUBSCRIPTION ONLY

**Objetivo:** O usuário faz login na conta ChatGPT/Claude normalmente. A Orquestra não utiliza `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, saldo de API ou faturamento adicional por token para GPT/Claude.

## Permitido

1. **Codex CLI oficial**, autenticado por `codex login` com conta ChatGPT, sujeito à elegibilidade e aos limites da assinatura.
2. **Claude Code CLI oficial**, autenticado pela conta Claude Pro/Max, sujeito à elegibilidade e aos limites da assinatura.
3. **Sign in with ChatGPT — uso do plano**, quando a aplicação for elegível e autorizada, seguindo a integração OAuth documentada para clientes open-source. Isso pode utilizar a **Responses API como transporte oficial**, mas **não** é uma chave de API paga. É necessário obter consentimento e permissões específicas, utilizar o endpoint oficial, `store=false`, `stream=true` e verificar limites. Não é um endpoint genérico ilimitado. Ver: https://developers.openai.com/siwc/token-sharing-open-source.
4. Um **gateway HTTP local** da própria Orquestra como *interface interna* para orquestrar a CLI oficialmente autenticada; esse gateway não é a API paga de inferência do provedor.
5. Hermes como orquestrador auxiliar opcional, preferencialmente acionando mecanismos oficiais por login e respeitando as restrições de cada provedor.

## Proibido

- Usar ou aceitar `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `CODEX_API_KEY` ou tokens de Console como fallback automático de faturamento GPT/Claude.
- Extrair cookies, copiar credenciais de navegador, reproduzir endpoints internos do site ChatGPT/Claude, simular clients não autorizados ou usar engenharia reversa para contornar pagamentos, limites, CAPTCHA ou autenticação.
- Transmitir credenciais/refresh tokens/arquivos de autenticação ao navegador ou Supabase.
- Ficar repetindo requests após `rate limit`, `quota exhausted`, autenticação revogada ou billing bloqueado. Parar e solicitar intervenção.
- Usar GPT/Claude para fazer deploy, merge, imprimir, transmitir notas fiscais ou modificar produção automaticamente.
- Marcar sucesso sem execução/testes comprovados.

## Regras de risco

- Credenciais de assinatura ficam somente na máquina autorizada; execução `127.0.0.1` com autenticação de gateway.
- Sessões sem login ou sem CLI instalada são `UNAVAILABLE`, nunca substituídas silenciosamente por uma API paga.
- Git worktree isolado; diretórios permitidos em arquivo local; verificação de árvore limpa.
- O executor principal segue os limites e termos do provedor; fila 24h não implica inferência ilimitada.
- O Claude Code pode usar login de assinatura no CLI; o uso de login Claude como API HTTP genérica do modelo não foi estabelecido, logo não está implementado.

## Evidência

- OpenAI SIWC: https://developers.openai.com/siwc/token-sharing-open-source
- OpenAI Responses OAuth: https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference
- Claude Code CLI: https://docs.anthropic.com/en/docs/claude-code/cli-usage
- Claude Code login: https://docs.anthropic.com/en/docs/claude-code/getting-started
