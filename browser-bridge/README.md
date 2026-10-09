# Orquestra Browser Bridge — Chrome MV3

Extensão mínima da Orquestra para conectar **o navegador local** ao painel.
A extensão NÃO se conecta à API da OpenAI/Anthropic e NÃO obtém OAuth ou chat
autorizado. Ela indica se a extensão respondeu e se existem abas abertas
em \`chatgpt.com\` e \`claude.ai\`. **Aba aberta ≠ usuário autenticado.**

## Instalação (Chrome/Opera base Chromium)

1. Baixe este repositório ou o arquivo ZIP da extensão e extraia em pasta privada.
2. Abra \`chrome://extensions\`, ative **Modo do desenvolvedor**.
3. Escolha **Carregar sem compactação** e selecione esta pasta \`browser-bridge\`.
4. Volte a https://orquestra-dev-app.vercel.app/, recarregue e abra **Conexões**.
5. Com ChatGPT e Claude em outras abas do mesmo perfil Chrome, clique
   **Verificar conexão**. Você verá somente "Aba aberta", não "Logado".

A extensão precisa da permissão \`tabs\` para saber a URL das abas abertas;
o Chrome pode descrever isso como acesso ao histórico. **Ela não lê histórico
navegado**, apenas URLs de abas atualmente abertas, não salva URLs e não envia
dados para nenhum servidor. Revise \`background.js\` antes de instalar.

A extensão injeta um único \`content.js\` **só** no domínio da Orquestra.
A página troca mensagens mínimas com ele usando \`postMessage\`; o worker
retorna dois valores booleanos. Não injeta scripts no ChatGPT ou Claude.
Não possui permissão \`cookies\`, \`webRequest\`, \`storage\`, host permissions
de chat ou acesso a conteúdo das mensagens.

Se a extensão for removida ou o navegador mudar de perfil, a tela indicará
"não detectada". O Chrome é responsável pela persistência das sessões nos
sites oficiais; a Orquestra jamais duplica cookies ou tokens.

### Limites

- Sem automação de leitura ou envio ao ChatGPT/Claude.
- Sem login de API ou utilização ilimitada de assinaturas.
- Sem execução de agentes no PC desligado.
- Acesso de conteúdo e automação exigiriam mecanismos oficialmente autorizados,
  avaliação de política e permissões explícitas adicionais.

### Referências

- https://developer.chrome.com/docs/extensions/develop/concepts/messaging
- https://developer.chrome.com/docs/extensions/reference/manifest/content-scripts
- https://playwright.dev/mcp/configuration/browser-extension
