# Orquestra 2.0 — Conversas (incremento UI, 21/10/2026)

## Objetivo
Tornar Conversas a entrada principal da Orquestra, sem fingir que o chat já está conectado a um modelo de IA e sem perder a interface anterior de missões diagnósticas.

## Alterações
- web-live/chat.html, chat.css e chat.js: interface responsiva de chat natural, sem projeto Git obrigatório.
- web-live/missions.html, missions.css, missions.js: preservam a interface e o fluxo diagnóstico legado, exceto nomes dos assets e link de retorno.
- supabase/functions/orq-chat/index.ts: create_thread idempotente por UUID do cliente; o servidor valida proprietário e título antes de devolver dados existentes.
- tests/test_chat_first.py continua garantindo as missões; tests/test_conversation_ui.py valida o novo chat.
- Nenhuma API de IA paga, OAuth browser ou credencial privilegiada no navegador.

## Fluxo após ativação separada do banco e da API
1. Usuário autentica pelo Supabase Auth existente.
2. A UI chama list_threads autenticado para comprovar que API e tabelas estão disponíveis. Se falhar, mostra bloqueio real e mantém Atividade acessível.
3. Cada envio usa UUID de thread e UUID de solicitação estáveis; salva mensagem real e turno bloqueado quando não há IA.
4. Se a conexão falha antes da confirmação, Tentar novamente reutiliza os mesmos identificadores.
5. Apenas respostas realmente persistidas com role assistant serão exibidas como mensagens de IA.

## Portas de segurança
- NÃO aplicar a migration SQL 008 ao Supabase compartilhado com CRM antes de ensaio em Postgres isolado, backup, teste RLS com duas identidades e revisão de segurança.
- NÃO implantar orq-chat com service_role antes da validação integrada da migração.
- Testar autenticação e retomada no navegador depois de ativar a API.
- O login pessoal OAuth do Hermes deve ser feito pelo operador no ambiente privado, sem enviar tokens ao chat.
- Projetos e Integrações permanecem no painel técnico anterior; redesenho futuro deve preservar funcionalidade.

## Rollback
A antiga UI de missões permanece em /missions.html; restaurar os antigos arquivos chat.* recupera a entrada visual anterior sem alteração de banco.
