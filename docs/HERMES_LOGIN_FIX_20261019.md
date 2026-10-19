# Hermes / ChatGPT OAuth — estado operacional e dependência real

**Data: 2026-10-19 · branch de desenvolvimento PR #18 · nenhuma publicação desta etapa.**

## Erro corrigido
A Orquestra oferecia um botão "ChatGPT → Entrar" que apenas abria `chatgpt.com`. Isso **não autentica o Hermes**. Foi removido. A interface `web-live/chat.html` agora oferece uma central Hermes OAuth com estado do executor, formato real do comando e bloqueio explícito quando o runtime está ausente. Não inventa challenge, QR code, consentimento ou sessão.

## Fluxo genuíno
O provedor desejado é `openai-codex` com OAuth *administrado pelo próprio Hermes*:
1. Inicializar **um** contêiner Hermes oficial revisado, fixado por versão/digest, isolado dos serviços do CRM e Argoplace. Reutilizar somente o projeto Railway separado `orquestra-cloud`, após aprovação explícita de ativação e custo.
2. Montar volume privado persistente em `/opt/data` com controle de acesso; não registrar tokens no Supabase, repositório, Vercel ou logs. Não expor terminal, painel ou porta Hermes à Internet sem uma camada de autenticação apropriada.
3. Autenticar **no próprio runtime** com `hermes auth add openai-codex --type oauth`. Hermes inicia o *device authorization grant*: emite URL/código; titular confirma apenas na página oficial. O modo `--browser` usa callback local fixo e não deve ser improvisado através de redirecionamento para Vercel.
4. Conferir com `hermes usage --provider openai-codex --json` e `python -m cloud.hermes_smoke` no mesmo perfil/volume. Ambos validam apenas prontidão; inferência requer teste separado. Definir modelo `openai-codex` via Hermes; desabilitar fallback pago e `auth.adopt_external_logins`.
5. O iniciador em `cloud/hermes_oauth_login.py` aceita apenas consentimento explícito e TTY privado; executa a CLI Hermes real e **não** captura/imprime credenciais. Até existir backend autenticado para retransmitir com segurança URL/código gerados pelo runtime, **a Orquestra web não pode iniciar o OAuth sozinha**.
6. A futura integração de um clique precisará de um controlador de autenticação *server-side* que verifique o dono do workspace e a autorização, limite sessões/tentativas e apresente somente a URL e o código temporário; nunca deve transmitir `auth.json` nem token de acesso. As verificações de sessão serão feitas no servidor.

## Limites atuais
- `orq-worker` está publicado e `ACTIVE` no Supabase Chatbot, mas é a fila; **não instala nem executa Hermes**.
- A Railway contém `orquestra-hermes-worker` **staged-create, sem deploy**, com imagem de diagnóstico que não inclui Hermes. As variáveis públicas de apontamento ao Chatbot ficaram somente staged. Nenhum executor está pareado.
- **Não está autorizado** merge, deploy da Railway, publicação de nova Edge Function ou alterações adicionais no banco/CRM neste pedido. A interface pop e o iniciador de autenticação estão apenas no PR.
- A solicitação `resolver login Hermes` corrige o fluxo visual, mas não constitui teste de autenticação concluída nem autoriza contornar o bloqueio anterior de deploy.
- Não usar acesso ao ChatGPT no navegador como prova de Hermes autenticado ou de inferência operacional.

## Dependência para desbloquear
Pedir **uma autorização específica** para ativar um runtime Hermes isolado na Railway, com volume privado e cota de recursos definida, sem modificar CRM ou serviços Argoplace. Após aprovado, implantar o runtime, gerar challenge real e solicitar ao titular somente a confirmação no provedor. Não solicitar senha ou token.

Docs: https://hermes-agent.nousresearch.com/docs/integrations/providers
      https://hermes-agent.nousresearch.com/docs/user-guide/docker
