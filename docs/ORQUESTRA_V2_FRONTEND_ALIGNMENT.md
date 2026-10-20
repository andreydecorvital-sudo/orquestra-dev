# Orquestra 2.0 — Frontend Alignment Brief
**Status:** direção de design para revisão conjunta ChatGPT ↔ Claude ↔ proprietário  
**Data:** 2026-10-20  
**Escopo:** UX, arquitetura de informação, linguagem visual e implementação FUTURA do frontend  
**Fora de escopo:** migrations, banco, filas, auth, execuções de IA, serviço Railway, integrações pagas e produção.

## 1. O produto que estamos desenhando

A Orquestra é a central pessoal de IA do proprietário: um único chat natural que coordena especialistas em engenharia, pesquisa, design, marketing, comércio, revisão e conhecimentos reutilizáveis do Origin. Conversar normalmente não exige escolher projeto ou preencher uma missão. Trabalhos complexos podem criar operações duráveis nos bastidores, com evidências, revisão e permissões.

**Regra de UX:** a Orquestra deve parecer um assistente pessoal premium antes de parecer um dashboard técnico. O sistema se adapta à intenção da conversa — o usuário não precisa se adaptar à arquitetura do sistema.

**Integridade:** a UI atual ainda envia um `diagnose` em `orq_tasks`, NÃO gera resposta genuína de IA. O redesign não deve fingir que isso já virou chat funcional. O design pode prever o futuro estado conversacional, mas a implementação usa indicadores honestos até o backend correspondente existir.

## 2. Diagnóstico do frontend atual (evidência de código)

- `web-live/chat.html` e `web-live/chat.css`: visual gamificado `MULTIVERSE HQ`, hero `Qual é a sua próxima missão?`, cartões de Lelouch/Nagi, ação `Nova missão`, seleção obrigatória de repositório, status Hermes, lista `missionList`.
- `web-live/chat.js`: o formulário `composer` cria tarefa `kind:'diagnose'` em `orq_tasks`; listas vêm de `orq_projects`, `orq_nodes` e `orq_tasks`. Modal de login usa Supabase Auth. Um projeto não deve ser criado automaticamente por uma pergunta.
- `web-live/index.html` + `web-live/styles.css` + `web-live/app.js`: painel avançado separado, com Modo navegador, Conexões, Visão geral, Projetos, Executores e tarefas. Tem UX e paleta diferentes da página de chat.
- `docs/ORQUESTRA_AI_HUB.md`: estabelece chat pessoal como experiência principal; `docs/ORIGIN_INTEGRATION.md` (PR #21): Origin como fonte de conhecimento privada, NÃO modelo ou agente fictício.
- Há visual e arquitetura duplicados entre chat e dashboard. Não criar uma terceira interface concorrente.

## 3. Direção visual escolhida para debate

**Conceito:** “Quiet intelligence / command center without noise”. Minimalismo sofisticado, foco em leitura, hierarquia clara, transparência de capacidades. Evitar neon excessivo, gradientes pesados, ficção visual de agente online, contadores fake, jargão interno, cores aleatórias e telas modal para tudo.

Proposta inicial de tokens (ajustável por Claude e proprietário antes de implementar):
- `--surface-base: #0D0F13` (grafite azulado); `--surface-sidebar: #11151C`; `--surface-raised: #181D26`;
- `--border: #2A313D`; `--text-primary: #F3F4F7`; `--text-muted: #A2ADBC`;
- `--accent: #A88AFF` (violeta suave); `--accent-quiet: #302841`; `--success: #69CFA9`; `--warning: #E5B467`; `--error: #E18E96`.
- Fontes: Geist/Inter ou equivalente com fallback de sistema; títulos moderados, sem display grotesco exagerado.
- Espaçamento em escala 4/8; raio 12–16px; bordas finas; sombra mínima; foco acessível visível.
- Tema escuro como proposta principal; estrutura preparada para tema claro futuro, sem exigir implantação nesta fase.
- Identidade visual própria da Orquestra, sem imitar marca, logotipo ou interface exata de ChatGPT/Claude.
- **Personagens Lelouch/Nagi:** no máximo avatares opcionais na página Equipe; nunca protagonismo na entrada do chat, nunca fazer parecer provedores conectados.

## 4. Arquitetura de informação v2

**Principal**
- **Conversas** — Nova conversa, histórico real por thread quando existir, pesquisa futura, retomada de contexto.
- **Projetos** — workspaces, repositórios autorizados, vinculações reais, decisões, contexto opcional.
- **Especialistas** — papéis de engenharia, pesquisa, design, marketing, operações, QA; disponibilidade verificada e provedores reais.
- **Atividade** — operações, filas, etapas, evidências, PRs, bloqueios e solicitações de autorização.
- **Conhecimento / Origin** — documentação e skills conectadas; exibir origem/versão, diferenciação “referência” versus “integrado”.
- **Integrações** — GitHub, Vercel, Supabase, Railway, Hermes/Codex, Claude e futuras IAs, com estados de conexão verdadeiros.
- **Configurações** — conta, permissões, preferências, custos/limites, auditoria.

**O usuário chega em Conversas.** O painel técnico permanece acessível e não desaparece; é reorganizado como visão avançada, não página inicial.

## 5. Wireframe de intenção (desktop)

```text
┌─────────────────────────┬──────────────────────────────────────────┬──────────────────────┐
│ ORQUESTRA               │ Conversa / contexto opcional             │ Contexto             │
│ [+ Nova conversa]       │                                          │ (ocultável)          │
│ Buscar (futuro)         │           Como posso ajudar?             │                      │
│                         │  Pesquisar   Criar   Resolver   Planejar │ Especialistas        │
│ CONVERSAS               │                                          │ Fontes e Origin      │
│ - Conversa atual        │  Conversa contínua e legível             │ Atividade            │
│ - Histórico             │  com artefatos e evidências              │ Aprovações           │
│                         │                                          │                      │
│ ESPAÇOS                 │                                          │ (só dados verificados│
│ Projetos                │                                          │ e relevantes ao caso)│
│ Especialistas           │                                          │                      │
│ Atividade               │                                          │                      │
│ Conhecimento / Origin   │                                          │                      │
│ Integrações             │                                          │                      │
│                         │ ┌──────────────────────────────────────┐ │                      │
│ Configurações           │ │ + Anexar   Pergunte qualquer coisa  ↑│ │                      │
│                         │ └──────────────────────────────────────┘ │                      │
└─────────────────────────┴──────────────────────────────────────────┴──────────────────────┘
```

Em tablet: barra lateral recolhível e painel direito em drawer. Em celular: conversa em largura total, composição fixa inferior segura, menu acessível, inspeção secundária por aba/drawer.

## 6. Páginas e interações

### Conversas
- Estado vazio elegante; uma pergunta comum (“olá”) não pode exigir repositório.
- Composer destacado, múltiplas linhas, Enter envia / Shift+Enter quebra, botão de envio com estado; anexo/voz somente quando recursos reais estiverem habilitados (caso contrário indisponível, não decorativo).
- Conversas continuam contextuais no backend futuro; não inventar histórico no localStorage.
- Fonte/modelo e estados visíveis quando relevantes: aguardando, respondendo, sem credencial, cota, interrompido.
- Pesquisa/projetos podem ser vinculados opcionalmente sem travar perguntas gerais.
- Resposta da IA não pode ser confundida com recibo de fila nem status de worker.

### Projetos
- Lista com vínculo real ao GitHub, estado de autorização e operações relevantes.
- Criação com loading, sucesso/erro claros; prevenir duplicações; preservar histórico já existente.
- Projeto é opcional em chats gerais; obrigatório apenas para atividades cujo executor precise de escopo.

### Especialistas
- Cards com papel, responsabilidade e provedor **efetivamente ligado**; estados “disponível”, “aguardando conexão”, “bloqueado”.
- Claude em UX/revisão somente se autorizado e disponível; Codex/Hermes como motor inicial apenas quando comprovado.
- A escolha “automática” deve exibir o plano real quando um trabalho exigir vários papéis.

### Atividade
- Reusar dados reais `orq_tasks`; estados, tentativas, timestamps, resultados e bloqueios. Sem tarefas falsas.
- Atividades derivadas de conversa aparecem como painel lateral sem transformar tudo em “missão”.
- Modal de aprovação apenas para ações com risco real; detalhar operação, escopo e consequência.

### Conhecimento / Origin
- Conector do Origin é fonte técnica privada e read-only, não “modelo inteligente” nem memória mágica.
- Diferenciar documentos e skills sugeridos, recuperados e implementados; citar caminho/commit.
- Não renderizar segredo, arquivos privados a outros usuários ou payload no frontend.

### Integrações e configurações
- Estados de conexão reais; Hermes OAuth não substitui login da Orquestra.
- Evitar popup que bloqueia toda navegação por uma plataforma desconectada.
- Cotas/estimativas só com fonte real, sem alegar “gratuito ilimitado”.

## 7. Contrato de preservação de backend

**PROIBIDO neste redesign** mudar:
- `supabase/`, `sql/` (incluindo RLS, Auth, Edge Functions e estrutura `orq_*`);
- `runner/`, `gateway/`, `cloud/`, `orchestration/`, Docker/Railway;
- `web-live/config.js`, chaves publicáveis, credenciais, URLs de backend;
- `main`, produção, banco Chatbot/CRM, Origin privado, Argoplace ou Mira.

**Permitido após aprovação visual:** alterar só `web-live` (HTML, CSS, JS frontend, assets próprios) com branch separada e PR; não romper `chat.html`, rotas atuais, login, sign out, consultas `orq_projects/nodes/tasks`, validação, gerenciamento de repositórios, regras de segurança, notificações ou refresh.

**Imprescindível:** não converter o atual `diagnose` em suposta resposta de chat no frontend. Se backend conversacional não existir, exibir modo atual honestamente e deixar novas capacidades como estado futuro. Seguir contrato das interfaces existentes até a implementação de chat ser autorizada em PR distinto.

## 8. Qualidade / revisão conjunta

**Antes de construir:**
- Claude propõe 1 direção visual principal e até 1 variante, criticando este documento com justificativas.
- ChatGPT valida coerência com frontend, arquitetura e backend; proprietário aprova direção.
- Um único conjunto de tokens e componentes; nenhuma variante de página antiga espalhada no projeto.

**Antes de liberar preview:**
- Desktop 1440×900; iPad paisagem 1024×768; tablet retrato 768×1024; celular 390×844 (incluindo rolagem, sidebar, composer e status).
- Legibilidade, contraste, teclado, estados vazios/loading/erro, form UX, sem overflow horizontal ou controles falsos.
- Fluxos reais: login/logout Supabase; lista/criação e seleção de projetos; listagem/status de tarefas; modal Hermes verdadeiro; sinalização de ausência de executor; prevenção de duplicados.
- Validar `tests/test_chat_first.py`, `tests/test_web_live_shared_database.py`, `tests/test_onboarding.py`, além dos testes relevantes e sintaxe JS. Atualizar testes que dependam de copy antigo somente se comportamento e segurança forem preservados.
- Não alegar “pronto” sem browser preview real e evidência de testes.

## 9. Papéis da colaboração

**Claude:** diretor de UX/UI; revisar hierarquia, tipografia, layout, tokens, estados, componentes, responsividade. Não mexer no backend nem criar login/inferência simulados. Especificar com precisão os arquivos frontend propostos e evidências visuais.

**ChatGPT:** guardião de arquitetura e contrato, avalia código atual e componentes, compara proposta de Claude com as limitações reais, implementa frontend somente após alinhamento, executa testes e prepara PR com screenshot de preview.

**Proprietário:** aprova escolha visual e mudanças consequenciais; não precisa aprovar pequenos ajustes reversíveis de alinhamento.

## 10. Mensagem de handoff para Claude

> Estamos redesenhando completamente o **frontend da Orquestra 2.0**. A Orquestra será uma central pessoal de IA conversacional, com especialistas, projetos, atividades, integrações e Origin como fonte privada de conhecimento. O chat natural é o produto principal, não “Nova missão”.
>
> Leia este documento como **fonte única de direção** e inspecione o frontend atual em `web-live/chat.html`, `web-live/chat.css`, `web-live/chat.js`, `web-live/index.html` e `web-live/styles.css`, respeitando o estado real dos recursos.
>
> Sua tarefa agora é **direção de arte + UX**, não implementação: critique a proposta, defina a experiência desktop/tablet/mobile, entregue a hierarquia das páginas e um design system coeso (tipografia, cores, espaçamento, cards, composer, estados) e aponte riscos de usabilidade. Não altere nenhuma API, backend, Auth, Supabase, Railway, worker, permissões, integrações ou produção. Não finja chats/respostas de IA onde só existe fila de diagnósticos.
>
> Traga uma direção final recomendada, as principais decisões e questões que dependem de aprovação visual do dono. Retornaremos sua proposta ao ChatGPT para consolidar um único plano de frontend antes de implementar.

**Fontes de referência:** `docs/ORQUESTRA_AI_HUB.md`, PR #20; `docs/ORIGIN_INTEGRATION.md`, PR #21. Backend e produção permanecem intocados.
