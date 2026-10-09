# Central de Conexões — Orquestra v1.2

O painel agora tem a aba **Conexões**, disponível sem login da Orquestra.

A extensão local \`browser-bridge/\` permite ao painel verificar se o Chrome
respondeu e se existem abas oficiais do ChatGPT e Claude abertas no mesmo
perfil. Ela **não confere autenticação** e não prova que a assinatura está
válida; abre-se cada site normalmente com a sessão do Chrome.

Instale a extensão pelo guia em \`browser-bridge/README.md\`. Não há leitura
de cookies, armazenamento do estado de login em servidor, scraping de chats,
envio de mensagens nem operações remotas automáticas.

O login separado do Supabase continua necessário apenas para a fila
persistente, projetos e executores. SIWC (Sign in with ChatGPT), quando
disponível para aplicativos elegíveis, é uma autorização oficial independente:
https://developers.openai.com/cookbook/articles/sign-in-with-chatgpt
**Nenhum cliente OAuth SIWC foi registrado nem ativado na Orquestra nesta fase.**

A etapa seguinte de integração automatizada, quando houver escopo e aprovação
do fornecedor, deverá usar OAuth/CLI oficial e armazenar qualquer segredo
somente localmente, nunca no cliente Vercel ou no Supabase público.
