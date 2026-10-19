# Reutilização do Supabase Chatbot pela Orquestra — migração segura

## Decisão autorizada

O titular confirmou que **o projeto chamado `Chatbot` no Supabase pode ser considerado para a Orquestra**. Não existe autorização para excluir tabelas, pausar projetos, reconfigurar Auth, sobrescrever dados ou misturar fluxos empresariais sem inspeção.

**Estado confirmado, 19/10/2026:** o conector Supabase usado neste chat retorna apenas a organização `saas` / projeto `winsgelyjddgqrxohkod`; o projeto `Chatbot` aparece no painel da outra organização e seu **ID ainda não foi confirmado**. Não aplicar SQL no projeto retornado pelo conector. O CRM publicado na Vercel anuncia o projeto `ydyzjpcmavqffdazteib`; até conferir o ID do Chatbot, não descartar dependência entre os dois.

O projeto `orquestra-dev` está pausado no plano gratuito. O projeto `Chatbot` deve **continuar ativo**: a opção aqui é hospedar as tabelas da Orquestra nele, não pausá-lo para liberar uma vaga. Isso compartilha cotas, Auth e fronteira de confiança do `service_role`; não equivale a isolamento físico de bancos. É necessário aceitar esses riscos operacionalmente antes da primeira escrita.

## Gate 0 — confirmar o projeto sem segredos

1. Abrir a página do projeto **Chatbot** no Supabase; coletar somente o identificador de 20 caracteres existente na URL `https://supabase.com/dashboard/project/<ref>`.
2. Conferir que o ID **não** é `winsgelyjddgqrxohkod` e comparar com `ydyzjpcmavqffdazteib` (referência atualmente publicada no CRM). Se coincidir, parar e revisar compartilhamento CRM/Orquestra antes de migração.
3. Verificar que o dashboard marca `Chatbot` como ativo; o painel da Orquestra antigo continua apontando para `kekxcvcgyexcbleifffq`, que está pausado.
4. Inspecionar somente a lista de funções Edge existentes e políticas Auth relevantes, para não substituir outro serviço.
5. Confirmar a conta/organização autorizada para o projeto. A conexão Supabase deste chat não concede acesso automaticamente a todas as organizações do navegador.

## Gate 1 — inventário estritamente read-only

Na **SQL Editor do Chatbot, e somente após confirmar o ID pelo dashboard**, consultar o conteúdo de `sql/000_shared_supabase_inventory.sql`. Essa consulta inventaria os objetos `public.orq_%`, a presença do `auth.users` e o `pgcrypto`. Não faz escrita.

Se o resultado for `REVIEW_EXISTING_ORQ_OBJECTS`, parar: `CREATE IF NOT EXISTS`, `ALTER TABLE` e `DROP FUNCTION` dos scripts antigos não podem ser aplicados sobre objetos desconhecidos.

Se `BLOCKED_AUTH_MISSING`, parar.

Se `NO_ORQ_OBJECT_COLLISIONS`, isso elimina **apenas colisões de nomes**. Ainda conferir o nome da Edge Function `orq-worker`, modelo de usuários Auth, RLS, destino do frontend, quotas e backups.

## Gate 2 — migração separada (requer autorização para mudar banco)

Os scripts `sql/001_init.sql` a `sql/005_hermes_kind.sql` foram escritos originalmente para um projeto **dedicado**. Não executá-los diretamente no Chatbot sem revisão das operações DDL e de privilégio; em especial `SECURITY DEFINER`, `GRANT/REVOKE` e `DROP FUNCTION` exigem auditoria para projeto compartilhado. É preferível planejar SQL de migração novo e explicitamente limitado ao namespace `orq_` e confirmar políticas RLS de isolamento `owner_id = auth.uid()`. Toda consulta e validação devem ocorrer na instância correta do Chatbot.

**Auth compartilhado**: contas criadas no `orquestra-dev` pausado não migram automaticamente. Para login no novo destino, usar uma conta Auth previamente autorizada no Chatbot ou provisionar uma conta específica aprovada pelo titular; não reusar cookies nem copiar senhas/tokens.

**Edge Function**: o endpoint `orq-worker` tem nome independente, mas usa service-role do projeto que hospeda os demais sistemas e exige verificação de origem, RLS e autorização antes do deploy. Não disponibilizar service-role para usuário ou frontend.

## Gate 3 — configurar o executor cloud, sem confundir projetos

A configuração de `cloud/diagnostic_runner.py` foi endurecida para exigir `ORQ_CLOUD_EXPECTED_SUPABASE_REF`, além da URL, e recusar inicialização caso não correspondam. A variável será preenchida **somente após** confirmar o ID do Chatbot; não inventar ID nem usar `winsgelyjddgqrxohkod`.

Os demais segredos (`ORQ_CLOUD_NODE_ID`, `ORQ_CLOUD_NODE_SECRET`, `ORQ_CLOUD_PROJECT_ID`) devem vir do pareamento na UI da Orquestra, no banco correto, e ficar selados na Railway. O serviço `orquestra-hermes-worker` está **staged** na Railway; não foi implantado. Nunca puxar segredos de CRM/Argoplace.

A UI pública `web-live/config.js` ainda aponta para o projeto pausado `kekxcvcgyexcbleifffq`: trocar somente a URL e a chave **publishable** do frontend após teste Auth/RLS. Nenhuma chave privada no Git.

## Critério de conclusão

- ID Chatbot confirmado, com dependência CRM avaliada;
- Inventário SQL read-only concluído, sem colisões inesperadas;
- SQL novo de isolamento revisado e aplicado apenas no projeto autorizado;
- RLS e Auth testados com dois usuários para comprovar segregação;
- Nova Edge Function registrada e testada sem tocar recursos Chatbot;
- UI Orquestra e worker Railway apontando para o mesmo ID e funcionando;
- Uma missão `diagnose` executada e registrada com evidência, antes de ligar Hermes.

**Sem esses passos: preparado, mas NÃO migrado.** Não declarar Chatbot conectado à Orquestra por existir apenas um PR.
