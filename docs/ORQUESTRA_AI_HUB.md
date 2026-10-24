# Orquestra AI — central pessoal e multiespecialista
Estado: fundação em branch de desenvolvimento; ainda não é chat funcional com IA.

## Experiência principal

Uma única conversa para qualquer assunto, como um assistente pessoal.
Não exigir projeto Git, escolher agente, abrir formulário de missão ou dizer
"próximo" para uma pergunta comum. Chat tem threads persistentes, contexto,
respostas genuínas do modelo, anexos e multimodalidade conforme integrações
reais disponíveis.

Quando o usuário pedir trabalho, a conversa poderá originar etapas
duráveis no executor sem deixar o chat. O assistente reporta evidências,
bloqueios e entregas; etapas internas não viram falsas mensagens de IA.
Ações irreversíveis continuam sujeitas a autorização específica.

## Coordenação e papéis (independentes do provedor)

- assistant: conversa pessoal, síntese, coordenação de especialistas
- research: pesquisa e verificação de fontes
- engineering: código, arquitetura, bugs e integração
- design: experiência visual, produto, UX e acessibilidade
- marketing: anúncios, conteúdo, campanhas e conversão
- commerce: estoque, catálogo, marketplaces e ERP
- review: revisão independente, testes e riscos

A escolha de uma especialidade não comprova que seu provedor está conectado.
O coordenador seleciona tarefas por intenção e complexidade; o executor
atribui uma sessão de IA real somente se o provedor tiver conexão, permissão,
quota e políticas verificadas. Nenhum fallback pago automático.

A primeira infraestrutura já validada inclui Hermes em contêiner privado na
Railway, configurado para openai-codex e GPT-6 Astra pelo operador. Ela NÃO
possui ainda conexão ao chat da Orquestra ou confirmação de inferência.
Claude, Gemini e outros conectores poderão entrar por especialidade depois de
serem conectados e testados separadamente. O sistema não presume acesso a
modelos via assinatura nem redistribui sessões privadas entre usuários.

## Fluxos distintos

1. Conversar: thread pessoal sem projeto -> modelo principal verificado ->
   resposta encadeada. Não criar orq_tasks para cada "olá".
2. Consultar especialista: conversa -> roteador -> especialistas autorizadas
   -> verificação de fontes -> síntese. Se não houver especialista online,
   comunicar a limitação, não fingir resposta.
3. Construir software: pedido no chat -> plano com critérios de aceite ->
   worktree autorizado -> código -> testes reais -> revisor independente ->
   patch/PR e evidências para aprovação.
4. Operar sistemas: conectores oficiais + escopo do proprietário; leitura e
   diagnóstico primeiro. Emissão fiscal, publicações, impressão, mensagens,
   gastos, credenciais, exclusões e produção exigem aprovação específica.

## Infraestrutura proposta

Frontend Chat na Vercel -> API de chat autenticada -> Supabase com RLS por dono
-> fila durável para turnos e operações -> worker privado na Railway com polling
outbound HTTPS -> Hermes e demais conectores, cada qual com política e credencial
própria. OAuth fica no volume privado do worker, nunca no browser ou no banco.

Entidades a preparar em migration review-only:
- orq_chat_threads: id, owner_id, título, escopo opcional de projeto, timestamps
- orq_chat_messages: id, thread_id, owner_id, role, conteúdo, evidências, timestamps
- orq_chat_turns: id, thread_id, owner_id, status, chave idempotente, lease,
  modelo realmente usado, bloqueios/cotas e vínculo opcional a trabalho
- orq_specialist_runs: papel, provedor, modelo, estados, evidências, revisão

RLS, key ownership, dois usuários de teste e auditoria da Edge Function são
obrigatórios antes de qualquer migração no Supabase Chatbot compartilhado com
CRM. Não aplicar DDL sem aprovação específica.

## Memória e qualidade

Memória pessoal e memória por projeto têm fontes, escopos e controles de
retenção distintos. O Orquestra não compartilha contexto pessoal, CRM, Origin,
Mira ou Argoplace entre empresas ou usuários automaticamente. O projeto
autorizado e a permissão vêm do backend, não do texto do modelo.

Para trabalhos complexos, especialistas atuam em etapas auditáveis; um
revisor separado compara alterações com critérios de aceitação. Critério de
conclusão = testes e evidências efetivas, não o agente dizer "pronto". Ciclos
de correção são limitados, retomáveis e param em erro de quota, credenciais,
teste inconclusivo ou necessidade de autorização humana.

## Implementado neste incremento

- orchestration/assistant_hub.py: papéis e planejamento de conversa vs trabalho
  com bloqueio de provedores ausentes, isolamento e autorização.
- tests/test_assistant_hub.py: casos de uso normais, especialistas e gates.

A função plan_assistance NÃO executa agentes, não consome tokens, não consulta
dados pessoais nem libera ações. É contrato de implementação, não serviço ativo.

## Próximas entregas em ordem

1. Revisar esquema, RLS e política de mensagens; migração separada review-only.
2. API conversacional com threads privadas, autenticação e idempotência.
3. Parear o worker Hermes na Railway e executar turnos de texto sem ferramentas.
4. Testar real "olá" + follow-up em uma thread, reabertura, limites e falhas.
5. Atualizar a interface para Nova conversa, histórico e especialistas reais.
6. Acrescentar memória, arquivos, pesquisa, trabalho em sandbox, revisão por
   outro modelo e automações com limites de custo e de segurança.

NÃO houve alteração em CRM, Argoplace, Supabase produtivo nem merge/deploy
em produção nesta preparação.
