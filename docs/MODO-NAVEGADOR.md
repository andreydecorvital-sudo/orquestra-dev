# Orquestra: Modo Navegador (sem CLI / sem API paga)

A Orquestra possui dois modos diferentes, com limites explícitos:

1. **Modo Navegador** (disponível sem conta Orquestra): prepara um prompt
   estruturado, abre os sites oficiais https://chatgpt.com/ e
   https://claude.ai/new, permite colar a resposta e gerar uma revisão para
   o outro modelo. **Nenhum dado é lido do navegador de terceiros.**
   Não existe comunicação automática entre os chats, tampouco inferência
   via API, OAuth não autorizado, cookies ou extensão.
2. **Fila de Agentes** (exige login próprio no Supabase): cadastra projetos,
   cria tarefas persistentes e pareia um executor Python com CLIs oficiais
   autenticadas, sem API paga como fallback.

## Como usar

Acesse https://orquestra-dev-app.vercel.app/ e escolha Modo navegador.
Descreva a missão, clique em Preparar, copie as instruções e abra um dos chats
oficiais. Na volta, cole a resposta na Orquestra e gere a revisão para o outro
modelo. Os textos ficam **apenas na memória da aba**; ao atualizar/fechar,
não são salvos. Não insira segredos, dados pessoais ou tokens em prompts.

## Sobre contas e login

Seu login ativo no Chrome em ChatGPT/Claude continua nos respectivos sites;
a Orquestra não visualiza essas sessões e não pode transformá-las em
consumo programático de API sem autorização específica. A função
"Sign in with ChatGPT" é separada da permissão para usar plano/créditos e
requer uma integração elegível, oficial e aprovada.

O login da própria Orquestra usa Supabase Auth, independente de ChatGPT e
Claude. Ele só é necessário para projetos/fila/executores persistentes.

## O que NÃO foi implementado

- Envios automáticos entre ChatGPT e Claude.
- Execução de agentes 24/7 através dos chats normais do navegador.
- Uma API de modelos ilimitada.
- Inclusão de dados de chat ou respostas no Supabase via modo navegador.
