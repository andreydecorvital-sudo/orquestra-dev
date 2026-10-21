# Acesso restrito: Orquestra no Auth compartilhado do Chatbot

O Supabase Chatbot é compartilhado com CRM. Um JWT válido do Chatbot **não prova** que seu dono pode usar a Orquestra. A Edge Function orq-chat só poderá atender requests autenticados cujo user.id esteja na allowlist do servidor.

- Defina ORQ_CHAT_ALLOWED_OWNER_IDS nas variáveis privadas da Edge Function (ou secrets do projeto), como IDs UUID separados por vírgula. Nunca publicar a lista no frontend ou em config.js.
- Obtenha os IDs por processo administrativo seguro, apenas para contas explicitamente autorizadas. Não copiar IDs de clientes do CRM por conveniência.
- Ausência/valor inválido da lista: HTTP 503 orquestra_not_configured (fail closed).
- Login válido sem permissão Orquestra: HTTP 403 orquestra_access_denied.
- Login expirado ou inválido continua 401; CORS restringe a origem autorizada.
- Antes do deploy, confirmar que a lista está configurada e que uma conta CRM não autorizada recebe 403. Testar ainda A/B e RLS.

O código não é deploy nem provisionamento da allowlist, não altera políticas de Auth ou CRM e não executa modelos.
