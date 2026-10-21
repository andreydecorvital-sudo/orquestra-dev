# Ativação segura da Orquestra no Supabase Chatbot (Free)

## Situação confirmada em 21/10/2026
- A instância `Chatbot` é o banco compartilhado com CRM e Orquestra.
- A organização está no plano Supabase **Free**, sem os backups diários automáticos dos planos pagos.
- SQL 008 passou em PostgreSQL descartável no GitHub Actions, mas ainda não foi aplicado a Chatbot.
- `orq-chat` está implantada e autenticação JWT é obrigatória; ela **falha fechada** sem `ORQ_CHAT_ALLOWED_OWNER_IDS`.
- `orq-worker` antigo continua intacto. Hermes não tem OAuth verificado.

## 1. Gerar exportação fora do repositório
No Windows, instale Docker Desktop e Supabase CLI oficiais. Execute `supabase login` em seu próprio computador (nunca compartilhe tokens no chat). No repositório execute:
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\backup-chatbot-windows.ps1
```
Ele gera quatro arquivos SQL (schema e dados do public e auth/storage) mais hashes e manifesto na pasta Documentos/Orquestra-Backups. Esses dumps incluem CRM e identidades; **não compartilhe ou envie a arquivos de chat/GitHub**, mantenha em unidade criptografada. Uma exportação bem sucedida NÃO prova que a restauração funciona. Teste recuperação em base isolada antes de liberar migração. Para uma cópia física/backup de plataforma, considere o plano Supabase adequado; não altere plano automaticamente.

## 2. Permitir o usuário da Orquestra, sem liberar os usuários do CRM
No painel do projeto Chatbot, Authentication > Users: identifique exclusivamente o UUID da conta humana autorizada. Na configuração privada Edge Functions > Secrets, defina `ORQ_CHAT_ALLOWED_OWNER_IDS` como os UUIDs autorizados separados por vírgulas. **Nunca** copie senha, usuário/token ou segredo para `web-live/config.js`, GitHub, logs ou chat.

Se usar a prévia experimental, as origens permitidas precisam ser explícitas. A Edge Function inclui apenas a URL permanente e a prévia específica já verificada. Para outras URLs, use o secret opcional `ORQ_ALLOWED_ORIGINS` com lista de URLs HTTPS completas separadas por vírgulas. Jamais usar `*` (coringa).

## 3. Liberar banco e testar
Depois de backup **restaurável** e configuração de acesso verificadas, execute a migração `sql/008_orquestra_chat_persistence_REVIEW_ONLY.sql` via Supabase migration no projeto **correto**, em transação atômica. Em seguida verificar `orq_chat_threads`, `orq_chat_messages`, `orq_chat_turns`, RLS, grants e security advisors. Fazer testes com duas contas sem compartilhar dados. O endpoint deve retornar 401 sem login, 403 para usuário CRM não autorizado, e 503 sem allowlist. Um turno `send` cria mensagem real e devolve `provider_not_connected` até Hermes autenticar; isso NÃO é uma resposta de IA.

## 4. Hermes
OAuth pessoal só pelo terminal privado da Railway, interativo, no CLI oficial. Não copiar tokens nem usar uma API paga sem autorização. Uma resposta real depende de worker conectado e teste E2E; nenhum botão da UI substitui a autenticação.

## Estado
Esta documentação e script não criam backup automaticamente, não publicam SQL, não alteram o CRM nem contratam serviços. São os passos verificáveis que faltam para uma ativação de produção.
