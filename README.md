# Orquestra Dev

Plataforma independente para coordenar tarefas de desenvolvimento, com **Lelouch** (planejamento), **Nagi** (execução), Codex/GPT (programação) e Claude Code (design/revisão).

## Situação atual

- Interface dark (preto, branco e vermelho) no Vercel.
- **Não há agentes online nem execução de IA em produção.** Nunca tratar tarefas locais demonstrativas como executadas.
- Um pacote técnico v1.0 independente prepara Supabase Auth/RLS, fila, worker e gateway de login, mas deve ser conectado e testado antes da ativação.

## Regra obrigatória — assinaturas

**GPT/Codex e Claude Code devem usar autenticação oficial da assinatura (quando elegível).** Não criar fallback para OpenAI API Key, Anthropic API Key, cookies extraídos, bypass de limites ou proxy de sessão não autorizado. APIs internas podem gerenciar tarefas, mas não substituem autorização do fornecedor.

## Operação segura

- Nada de segredos no navegador ou no GitHub.
- Nunca compartilhar banco, service_role ou tokens com Argoplace/CRM.
- Git worktrees isolados; PRs e revisão antes de produção.
- Execução 24/7 exige worker autenticado continuamente disponível, não apenas Vercel e fila.
- Provedores e workers só ficam **ONLINE** após teste end-to-end real.

## Próximas integrações

1. Importar o restante do pacote técnico v1.0 e validar testes.
2. Vincular Vercel ao GitHub e definir a raiz do frontend.
3. Criar projeto Supabase exclusivo **após aprovação da organização e do custo informado pela plataforma**.
4. Configurar login das CLIs oficiais no dispositivo executor, parear worker e testar uma tarefa de diagnóstico.
5. Testar Codex, Claude e colaboração, gerar patch/PR com logs e aprovações.

> **Privacidade:** este repositório foi criado como público. Torne-o privado antes de incluir informações operacionais de empresas.
