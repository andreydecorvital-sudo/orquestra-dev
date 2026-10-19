# Orquestra → Argoplace: piloto de execução verificável

O piloto é limitado a um workspace autorizado. Não executa produção, não concede novas permissões e não substitui as instruções de AGENTS.md.

## 1. Verificar o executor local

No clone da Orquestra, execute:

    python -m runner.preflight

O comando examina a existência do arquivo local de pareamento, valida sua estrutura usando o validador existente, verifica se os diretórios Git autorizados estão presentes e, somente se a execução já estiver ligada, consulta os estados de login nas CLIs oficiais Codex e Claude. Não contata Supabase, não acessa dados do marketplace, não inicia agentes e não revela caminhos locais, IDs, segredos ou conteúdo dos repositórios.

Interpretação:

| Status | O que significa | Próximo passo |
|---|---|---|
| blocked | Configuração inexistente/inválida ou pasta Git não mapeada | Consultar docs/PRIMEIRO-ACESSO.md e realizar o pareamento privado |
| diagnostics_ready_locally | Mapeamento Git detectado, IA desligada | Fazer primeiro job remoto de diagnóstico num sandbox |
| login_required | Execução habilitada mas nenhuma CLI autenticada | Fazer login oficial no dispositivo |
| code_ready_locally | Há mapeamento Git e pelo menos uma CLI autenticada | Provar tarefa Codex no sandbox e checar patch e revisão |

Atributos de evidência backend=not_checked, tests=not_run e end_to_end_verified=false nunca se tornam verdadeiros somente com este comando.

## 2. Testar a cadeia completa

1. Autorizar apenas um repositório de teste sem segredos; parear executor e cadastrar projeto no painel.
2. Rodar tarefa diagnose e verificar o ID em fila, claim, execução e relatório.
3. Autenticar CLI oficial, habilitar execução local explicitamente e rodar uma mudança pequena em worktree isolado.
4. Verificar patch salvo, checks reais e nenhuma alteração em produção.
5. Avaliar o PR #16 (recibos duráveis da Orquestra) e testar que a perda de ACK não provoca execução duplicada.
6. Só depois permitir um CLONE ISOLADO e explicitamente autorizado de vitalhub, com missões de código sem deploy/merge/banco/fiscal/impressão.

## 3. Conclusão real de missões

A Orquestra deve separar tarefa técnica executada de objetivo comercial verificado. Os scripts de package.json da Argoplace não podem ser executados livremente: precisam de comandos e ambientes aprovados, limites de tempo, revisão de dependências e isolamento.

Etapa seguinte: testes específicos e verificadores independentes para expedição, fiscal, catálogo e Mira. Uma tarefa só será marcada como objetivo verificado depois de patch preservado, testes realmente executados e critérios de aceite comprovados; senão marcar review_required, blocked ou not_tested.

## 4. Limites atuais

- Origin PR #23: contrato genérico de loops ainda em revisão. A Orquestra continua responsável por execução e permissões.
- Orquestra PR #16: journal de entrega ainda em revisão; o preflight não o substitui.
- Banco Supabase: confirmar a disponibilidade no projeto/conta correta, sem criar recursos pagos por suposição.
- Um deploy READY da interface na Vercel não comprova executor, autenticação remota nem execução 24/7.
