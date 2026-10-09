# Orquestra + Hermes (local, sem API paga obrigatória)

**Status:** conector desenvolvido, não emparelhado a nenhuma máquina do usuário.

O [Hermes Agent](https://hermes-agent.nousresearch.com/docs/user-guide/features/api-server)
dispõe de um servidor OpenAI-compatible em \`http://127.0.0.1:8642/v1\`
com \`API_SERVER_KEY\`. O executor Python da Orquestra faz chamadas **somente
por loopback**, com chave lida de \`%LOCALAPPDATA%\hermes\.env\` no Windows,
sem transmiti-la ao Supabase, Vercel, GitHub ou navegador.

## Preparação (uma única vez, no Windows do executor)

1. Instale o Hermes pela [página oficial](https://hermes-agent.nousresearch.com/docs/getting-started/installation/). Confira o código do instalador antes de executá-lo. Não é necessário WSL.
2. Abra PowerShell e autentique com seu navegador:

   \`\`\`powershell
   hermes auth add openai-codex --browser
   hermes model
   \`\`\`

   Escolha o backend **OpenAI Codex usando a assinatura elegível**, não a
   API key tradicional. Isso respeita limites da conta e não dá acesso
   ilimitado ao chat normal do Chrome. **Não habilite Nous Portal/OpenRouter
   ou fallback pago** sem querer.

3. Dentro de seu clone do repositório, rode
   \`powershell -NoProfile -File .\runner\prepare-hermes-windows.ps1\`.
   O script exige Hermes instalado, configura a API apenas em
   \`127.0.0.1:8642\`, gera uma chave aleatória forte (ou preserva uma
   chave existente), desliga CORS de navegador e protege ACLs.
   **Ele não inicia execução autônoma.**
4. Na ferramenta \`hermes tools\` ou nas configurações próprias do Hermes,
   desative **todas** as ferramentas do perfil \`api_server\`.
   O adaptador rejeita qualquer \`/v1/toolsets\` em que uma ferramenta
   esteja ativa. A condição é deliberada: Hermes API padrão pode executar
   terminal, arquivos e navegadores. Prompt "não execute" não é segurança.
   Use perfil Hermes separado para a Orquestra se você usa ferramentas
   em outras conversas.
5. Execute \`hermes gateway\` no computador. Ele deverá escutar apenas em
   \`http://127.0.0.1:8642\`.
7. Cadastre projeto de teste e pareie um executor na Orquestra, via aba
   Executores. No arquivo privado \`runner/agent-worker.json\`, habilite:
   
   \`\`\`json
   {"allow_execution": true, "allow_hermes_planning": true}
   \`\`\`

   Essas são **duas propriedades do arquivo de configuração já criado**;
   não substitua o restante do JSON por esse exemplo.

8. Inicie \`python -m runner.agent_worker\`. Quando o Hermes responder
   a \`/v1/models\` e \`/v1/toolsets\` em modo seguro, o executor anuncia
   capacidade **hermes**. Crie tarefa da modalidade Hermes no painel.

## O que a missão Hermes entrega

Somente texto de planejamento/revisão e recomendações de testes, registrado
na fila Supabase. Não altera arquivos, executa comandos, faz push/deploy,
compra serviços ou consome uma API paga como fallback.

## Política de custo e falha

- API_SERVER_KEY **não é OPENAI_API_KEY**. É apenas uma senha local
  do servidor Hermes.
- O Hermes precisa de provedor/modelo configurado, e o OAuth do Codex
  exige elegibilidade e limitações reais do ChatGPT.
- \`/v1/models\` disponível **não prova** que um modelo responde;
  somente um teste real de inferência no PC confirma isso.
- Resposta de erro HTTP, timeout, falta de chave, ferramenta ativa ou
  configuração insegura **falham sem fallback pago**.
- O backend gratuito não executa Hermes por conta própria com o PC desligado.

## Referências
- https://hermes-agent.nousresearch.com/docs/user-guide/features/api-server/
- https://hermes-agent.nousresearch.com/docs/reference/cli-commands/
- https://hermes-agent.nousresearch.com/docs/reference/toolsets-reference/
- https://hermes-agent.nousresearch.com/docs/user-guide/windows-native/
