# ORQUESTRA CLI · Hermes Kanban com Codex (piloto local)

Este iniciador **não substitui** a fila Supabase anterior nem libera qualquer produção. É um modo adicional que usa o dispatcher nativo do Hermes e não necessita de Vercel/Supabase para criar tarefas na máquina local.

## Pré-requisitos

- Windows CMD, Python 3.10+, Git, Hermes Agent atualizado, Codex CLI oficial **e Gemini CLI opcional para o comando `equipe`**. Instale Gemini CLI com `npm install -g @google/gemini-cli` e execute `gemini` → **Sign in with Google**. Sem chave Gemini/Google API paga.
- Repositórios irmãos da pasta `orquestra-dev`: `origin` e `vitalhub`. Opcional: `ORQUESTRA_PROJECTS_HOME` apontando para a pasta que contém ambos.
- Autenticação local `codex login`, Hermes com perfil `nagi` no provedor **ChatGPT or Codex Subscription**. Não configure APIs pagas ou fallbacks inesperados.
- Dentro de `hermes -p nagi --tui`, use `/codex-runtime codex_app_server` e reinicie a sessão para ativar o runtime. Validar o resultado real antes de despachar.
- O perfil deve ter permissões restritas; um prompt não substitui sandbox. Codex workers são sandboxed quando corretamente configurados; verifique as permissões do seu runtime.

## CMD 1 — preparar

```cmd
cd /d "%USERPROFILE%\Projetos\orquestra-dev"
ORQUESTRA.cmd doctor
ORQUESTRA.cmd preparar
hermes -p nagi model
hermes -p nagi --tui
```

Dentro do Hermes, digite `/codex-runtime codex_app_server`, encerre e reabra a sessão. Termine `codex login` se ainda não estiver autenticado. Para primeiro teste, execute um chat curto como Nagi.

## CMD 2 — iniciar o despachante

```cmd
ORQUESTRA.cmd gateway
```

**Este CMD deve permanecer aberto.** O gateway inclui o dispatcher Kanban. Apenas criar perfis e quadros não inicia tarefa nenhuma.

## CMD 3 — tarefas e acompanhamento

```cmd
ORQUESTRA.cmd teste
ORQUESTRA.cmd acompanhar origin
ORQUESTRA.cmd equipe argoplace "Investigar por que etiquetas Shopee ficam bloqueadas"
ORQUESTRA.cmd acompanhar argoplace
ORQUESTRA.cmd status origin
```

O teste usa workspace scratch, não um repositório. Acompanhe até a tarefa estar `done`, `review` ou `blocked`; veja detalhes com `hermes kanban --board origin list`, `show <ID>`, `runs <ID>` ou `log <ID>`. Se ficar eternamente `ready`, confira `hermes gateway status`, login do perfil e `hermes kanban --board origin diagnostics`.

Depois do teste, crie um diagnóstico em worktree **isolado**, sem alterar seu checkout da main:

```cmd
ORQUESTRA.cmd investigar argoplace "Examinar origem dos erros na expedição e recomendar testes"
ORQUESTRA.cmd acompanhar argoplace
ORQUESTRA.cmd investigar origin "Mapear skills de filas que podem ajudar a Argoplace"
```

Worktrees isolados ficam em `%LOCALAPPDATA%\Orquestra\worktrees` e **não são removidos automaticamente**. Nenhum push, PR, deploy ou merge é executado pelo iniciador. O agente poderá usar ferramentas locais conforme a configuração real do perfil; mantenha permissões mínimas, não dê credenciais de produção e revise resultados.

## Gemini + Codex sem Claude

- `ORQUESTRA.cmd equipe argoplace "TAREFA"` chama primeiro Gemini CLI com `--approval-mode plan` em pasta temporária, enviando só regras de projeto (AGENTS.md, e START_HERE.md no Origin) e a instrução. Retorna um plano e cria um card Hermes para o Nagi via login ChatGPT.
- Gemini CLI precisa de login Google já feito em sessão interativa `gemini`. A automação **não** usa `GEMINI_API_KEY`, `GOOGLE_API_KEY`, fallback de API paga, nem envia credenciais para Supabase.
- Ao atingir limite ou falhar no login do Gemini, a automação para; não consome a franquia GPT silenciosamente.
- Gemini opera em modo plan e diretório temporário, mas **isso não é isolamento de sistema operacional**; mantenha a execução restrita a máquina e projetos de confiança. O Gemini não recebe o diretório de código; Nagi só usa uma cópia Git separada.
- Claude continua desativado na CLI nova. **Grok Bot** é um produto de agentes com computador em nuvem e uso próprio; sua assinatura não garante automaticamente que o mesmo login funcione no Hermes. Se sua conta xAI também for elegível para o OAuth do Grok via Hermes, teste `hermes auth add xai-oauth` em perfil separado e a resposta real antes de integrá-lo. Não use `XAI_API_KEY` nem fallback pago sem autorização.

## Limitações atuais

- Nagi é um perfil Hermes cujo runtime pode usar Codex. Outros perfis ainda não estão configurados nem autorizados pelo iniciador.
- Não configura Claude e não transforma assinatura ChatGPT em API para os clientes da Argoplace.
- A primeira cadeia é Gemini (planejamento) → Hermes Kanban → Nagi/Codex (investigação); revisão posterior automática depende de validar os agentes e de acrescentar novos cartões de handoff.
- `doctor` valida comandos e pastas, **não garante** inferência, limites da assinatura ou gateway ativo.
- Hermes Kanban usa SQLite local e dispatcher local (não uma fila multi-servidor). Para executar tarefas com PC desligado é necessário um executor autorizado em máquina ligada.

## Referências

- https://hermes-agent.nousresearch.com/docs/user-guide/features/kanban
- https://hermes-agent.nousresearch.com/docs/user-guide/features/codex-app-server-runtime
- https://geminicli.com/docs/get-started/authentication/
- https://geminicli.com/docs/cli/headless/
- https://hermes-agent.nousresearch.com/docs/guides/xai-grok-oauth/
- https://docs.x.ai/grok-bot/overview
