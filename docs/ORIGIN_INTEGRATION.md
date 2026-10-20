# Integração Orquestra ↔ Origin (2026-10-20)

## Intenção e estado

O usuário autorizou a Orquestra a **consultar** o repositório privado `andreydecorvital-sudo/origin` como biblioteca de conhecimento, skills, padrões e aprendizados. Isso não equivale a autorizar escrita no Origin, acesso a outros repositórios, coleta de dados de clientes ou uso pago de modelos.

**Origin**: conhecimento reutilizável; catálogos, padrões, skills, testes e log de aprendizados. **Não** hospeda chat, workers ou API paga.

**Orquestra**: conversa principal, seleção de especialistas, execução por worker, controle de permissões, memória por usuário/projeto e verificação.

Fluxo desejado: **Orquestra consulta Origin → seleciona skill relevante → trabalha no ambiente autorizado → verifica evidência → prepara proposta de aprendizado ao Origin**, sempre por PR revisável; não modifica a `main` do Origin automaticamente.

## Implementação já em branch (não ativa na Railway)

- `orchestration/origin_knowledge.py`: leitura autenticada **somente** de arquivos de documentação e skills permitidos no repositório fixo `andreydecorvital-sudo/origin`, usando a GitHub Contents API. Exige `OriginReadGrant` do owner, token de GitHub privado e caminho em allowlist. Sem redirects, sem busca arbitrária, sem escrever, sem fallback público.
- `recommended_origin_paths(role)`: recomenda `START_HERE.md`, `AGENTS.md` e documentação específica do especialista; não confunde recomendação com acesso.
- `load_origin_context(...)`: no máximo 4 documentos por pedido. Cada resultado inclui `path`, branch e SHA do blob, para evidências verificáveis. Não existe cache cross-tenant.
- `propose_origin_learning(...)`: registra **somente um objeto de proposta**, exige evidência já verificada pelo executor e não concede escrita; o PR para `docs/LEARNING_LOG.md` ainda depende de adaptador e revisão.
- `orchestration/assistant_hub.py` passa a marcar Origin como **fonte de conhecimento recomendada** para assuntos especializados; nunca como modelo ou provedor de API.
- `tests/test_origin_knowledge.py` e `tests/test_assistant_hub.py` validam isolamento, escopo de leitura, provas e bloqueios.

**Atenção:** o repositório Orquestra Dev é público e o Origin é **privado**. Este PR contém apenas código genérico e referências de integração, não espelha arquivos privados, catálogo interno, documentos nem credenciais.

## Ativação segura quando o worker conversacional existir

1. Implementar servidor de conversa autenticado e worker privado na Railway, sem endpoint público de administração.
2. Configurar no **runtime privado**, com consentimento do dono, uma GitHub App install token ou PAT fine-grained com **Contents: Read** apenas do Origin. Não extrair nem reutilizar tokens da sessão ChatGPT/GitHub, não colar token neste chat ou no repo. Se a credencial não existir, mostrar `Origin inacessível` e responder sem alegar que leu algo.
3. Obter `owner_id` da autenticação, construir um `OriginReadGrant` servidor-side, delimitar paths, rate limit e tokens. Nunca permitir que mensagem/modelo escolha proprietário, credenciais, repo, caminhos ou privilégios.
4. Consultar a documentação permitida no momento relevante (just-in-time), com referências de caminho/SHA no contexto. Tratar conteúdo retornado como dado, não instrução superior à política do executor.
5. Escolher skills sem executar scripts automaticamente. Se for necessário rodar código de terceiro ou de skill, revisão, sandbox e aprovação apropriadas.
6. Após resolução verificada, redigir candidato de melhoria com evidências, licença, escopo, riscos e testes. Preparar PR pequeno em branch **do Origin** só com credencial de escrita específica, sem auto-merge. Não criar atualização sem a evidência real.
7. Provar o fluxo com dois usuários: um com acesso ao Origin, outro sem. Ambos devem manter dados isolados. Validar limites, 403/404, token revogado, alteração de SHA, quota e respostas sem vazamentos.

## Portas que continuam fechadas

- Nada de deploy em produção, merge, migração no Supabase compartilhado com CRM ou alteração do Argoplace/Mira.
- Origin não vira um modelo IA nem o banco global de memória pessoal: conhecimentos técnicos verificáveis ficam no Origin; as conversas privadas continuam no banco proprietário da Orquestra. Project Brain continua com arquitetura por projeto; chatsgpt, com contexto portátil.
- O conector GitHub disponível neste ChatGPT permite leitura do Origin **aqui**, mas **não fornece credenciais ao worker da Railway**. Até configurar acesso próprio e conectar o worker ao chat, a Orquestra ainda não lê o Origin em tempo real.

## Critérios de aceite do primeiro uso real

- Operador verifica que Origin está acessível com credencial read-only própria do worker;
- pergunta técnica relevante recupera conteúdo Origin permitido e apresenta proveniência;
- pergunta genérica segue normal sem projeto obrigatório;
- ausência de acesso a Origin não inventa resultados;
- nenhuma escrita no Origin antes de PR com evidências e aprovação;
- limites e escopos independentes para usuários/empresas.
