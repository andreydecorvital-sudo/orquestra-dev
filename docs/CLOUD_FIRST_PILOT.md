# Orquestra Cloud — diagnóstico inicial sem PC

## Estado real

A Orquestra já publica o painel na Vercel. A execução Python, as CLIs Codex/Claude e o Hermes são componentes separados. Este PR cria **somente a imagem de um executor de diagnóstico na nuvem**, pronta para revisão e configuração numa infraestrutura autorizada. Não inicia um novo serviço nem altera produção.

A primeira fase da nuvem serve para **provar o caminho de rede e autenticação da fila** sem risco de invocar modelos, emitir notas, enviar mensagens, imprimir etiquetas ou acessar dados da Argoplace.

## Topologia proposta

- Vercel: painel (já existente).
- Supabase **exclusivo da Orquestra**: autenticação, fila, eventos e dispositivos; precisa ser confirmado na conta correta.
- Worker em contêiner persistente: no piloto, apenas `diagnose` e `integrations`. Não usar o Supabase da Argoplace por conveniência.
- Sandbox Git: clone efêmero somente de `https://github.com/andreydecorvital-sudo/orquestra-dev.git` público. Nada de clone da Argoplace nesta fase.
- O Origin fornece contexto somente após integração aprovada; não concede permissões nem roda código.
- Hermes: conector local atual **não foi ligado à nuvem** e não está em execução. A decisão posterior exige um backend de autenticação oficial e licenciado, isolamento e prova de custo/quota; jamais exportar cookies ou tokens de sessão do PC.

## Preparação da imagem para o piloto

Contexto Docker: raiz do repositório; Dockerfile: `cloud/Dockerfile`. O Dockerfile copia apenas arquivos Python explícitos, não copia configs locais ou segredos. Usa usuário não-root.

Variáveis secretas do contêiner a provisionar **apenas com dados autorizados do banco dedicado da Orquestra**:

- `ORQ_CLOUD_SUPABASE_URL`: HTTPS de um projeto Supabase dedicado.
- `ORQ_CLOUD_NODE_ID`: UUID do executor pareado para o dono correto.
- `ORQ_CLOUD_NODE_SECRET`: segredo de 64 caracteres hexadecimais, fornecido no pareamento; nunca versionar, mostrar no frontend ou colar no chat.
- `ORQ_CLOUD_PROJECT_ID`: UUID do projeto de piloto registrado no painel, cuja única pasta autorizada será o clone público `orquestra-dev`.

Para iniciar a imagem **após aprovação operacional**:

    python -m cloud.diagnostic_runner

O contêiner verifica esses valores sem exibi-los, clona o GitHub público num diretório temporário e inicia `runner.agent_worker.run_worker(config)` com uma configuração criada **em memória**. Não utiliza `runner/agent-worker.json` no contêiner.

**Política fail-closed:** `allow_execution=false`, `allow_hermes_planning=false`. Se `ORQ_CLOUD_ENABLE_CODE=true`, a inicialização falha. Não há configuração para trocar o clone público por um repo privado. As únicas capacidades anunciadas são `diagnose` e `integrations`.

## Aceite antes de ampliar o escopo

1. Confirmar custo e permissões do serviço persistente; não criar ou pagar recursos automaticamente.
2. Verificar que o banco escolhido é da Orquestra, que o device está pareado e que o serviço não usa o banco operacional da Argoplace.
3. Fazer um único diagnóstico remoto end-to-end, registrando tarefa, claim, heartbeat, resultado e evidência.
4. Simular retomada de worker sem repetir operações; incorporar com revisão o PR #16 (journal durável).
5. Somente em ambiente isolado e após nova revisão, criar um executor Codex Cloud legítimo com testes reais. O login de assinatura no navegador **não é** uma API para executar agentes livremente de um servidor.
6. Analisar Hermes Cloud como módulo opcional de planejamento/revisão, separado de permissões para shell, deploy ou dados reais.

## Limites e segurança

Este PR **não demonstra nuvem ativa** e não faz deploy, merge, migrations, gestão de segredos, gastos ou chamadas de modelo. Um deploy READY da UI e um teste de código local não equivalem ao teste completo do serviço remoto. Execução 24/7 depende de recursos e orçamento reais, do executor ligado e das quotas aplicáveis.
