# Orquestra — chat privado, incremento 1 (21/10/2026)

Estado: PR de desenvolvimento, sem migração executada, Edge Function implantada ou inferência.
Objetivo: começar a persistir conversas privadas de forma verificável sem exigir projeto Git.

## Entregue
- sql/008_orquestra_chat_persistence_REVIEW_ONLY.sql: somente três tabelas novas sob prefixo orq_; RLS de leitura por proprietário e toda escrita pelo servidor autenticado; bloqueio se houver objetos conflitantes.
- supabase/functions/orq-chat/index.ts: endpoints autenticados create_thread, list_threads, read_thread e send; último guarda uma mensagem e um turno bloqueado, com resposta explícita de que não houve inferência.
- Uma mensagem não inicia missão diagnose nem disfarça resposta de IA. Envio idempotente por client_request_id UUID, transação no banco, limite de 10 turnos/minuto e 300/dia por proprietário.
- tests/test_chat_persistence_contract.py: contrato estático de segurança e ausência de API paga.

## Portas de segurança antes da ativação
1. Revisão humana específica da migração no Supabase Chatbot (também usado pelo CRM); backup e plano de reversão. Não aplicar pelo GitHub merge.
2. Testar em banco descartável: migração, RLS com dois usuários, negação de escrituras diretas, sessões expiradas, mesmo client_request_id em chamadas concorrentes e owner errado.
3. Inspecionar políticas/grants das tabelas novas, executar os security advisors do Supabase e revisar a Edge Function.
4. Deploy independente de orq-chat com URL origin permitida; jamais colocar service_role no browser.
5. Ligar web-live à API somente depois dos testes de ponta a ponta. Nenhum resultado de IA deve ser mostrado enquanto não houver executor autorizado.
6. Parear nó Orquestra separado do host Hermes, autenticar OAuth oficial no serviço privado, testar uma geração sem ferramentas e só então planejar conectar turnos reais; Claude/Origin depois.

## Critérios de aceite
- Sem mudanças no CRM, no schema Auth, nos fluxos fiscais ou no Argoplace.
- A conta A não lê threads/mensagens da conta B, nem consegue forjar mensagens assistant.
- O mesmo client_request_id salva uma única mensagem, mesmo com repetição ou corrida; conteúdo divergente retorna conflito.
- Offline/provider não conectado: mensagem e bloqueio persistem, nunca uma resposta inventada.
- Nada em produção, nenhum custo de inferência, nenhuma senha ou OAuth no GitHub.

Limites: API e SQL preparados, não integrados à UI e não aplicados ao banco. A UI antiga de diagnose continua funcionando como antes; executores ainda exigem pareamento.
