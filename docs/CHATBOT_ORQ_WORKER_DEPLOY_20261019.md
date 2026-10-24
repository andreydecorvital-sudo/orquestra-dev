# Orquestra Chatbot — execução autorizada em 2026-10-19

## Escopo e autorização
O titular autorizou **exclusivamente** o deploy da Edge Function `orq-worker` no Supabase Chatbot `ydyzjpcmavqffdazteib`, validação de segurança, preparação do executor e um diagnóstico sem alterações externas. **Não** autorizou merge, deploy Railway nem outras mudanças em produção.

## Realmente executado
- Conexão correta Supabase: `Supabases` / organização `wdctctuiebcxsmtsncqn`, projeto `ydyzjpcmavqffdazteib`, estado `ACTIVE_HEALTHY`. O outro conector `Supabase` aponta para a organização `saas` e NÃO deve ser usado.
- Antes do deploy: `list_edge_functions` retornava 0 funções. Depois do deploy: **somente** `orq-worker`, `ACTIVE`, versão 1, ID `8632716f-7030-42be-a313-1ac1784678b8`, `verify_jwt=false` exigido pelo protocolo de dispositivos autenticados por segredo; cadastro de dispositivo exige JWT do usuário validado no código. O `index.ts` instalado coincide integralmente com `supabase/functions/orq-worker/index.ts` da branch do PR #18.
- Pós-verificação SQL **somente leitura**: 4 tabelas `orq_`, todas com RLS; leitura anônima negada; coluna `orq_nodes.secret_hash` inacessível a `authenticated`; 3 RPCs de execução sem `EXECUTE` para `anon` ou `authenticated`, e todas `SECURITY DEFINER`; resultado `STATIC_SECURITY_CHECKS_PASS`.
- `pg_policies` confirma `owner_id = auth.uid()` em SELECT das quatro tabelas e em INSERT de projetos e missões. Não há política anônima liberando acesso aos objetos `orq_`.
- Contagens read-only: 1 usuário Auth no projeto, 0 projetos Orquestra, 0 nós pareados, 0 missões, 0 eventos; CRM tem 1 tenant e 1 tenant_membership. **Nenhum usuário, projeto, nó ou missão foi criado por esta operação**. Os dados do CRM não foram alterados.
- Railway `orquestra-cloud` (ambiente `sandbox`): worker `orquestra-hermes-worker` continua **staged-create**, sem deployment; somente duas configurações públicas foram **staged**, não aplicadas: `ORQ_CLOUD_SUPABASE_URL=https://ydyzjpcmavqffdazteib.supabase.co` e `ORQ_CLOUD_EXPECTED_SUPABASE_REF=ydyzjpcmavqffdazteib`. A flag `ORQ_CLOUD_SHARED_DB_AUDITED` **NÃO foi marcada**; uma checagem com dois usuários precisa ser feita primeiro.

## Limites do diagnóstico
- Foi realizado um **diagnóstico administrativo somente leitura** da estrutura e autorização; **não foi executada uma missão real da fila**, porque não existe nó pareado e o titular proibiu deploy da Railway.
- O isolamento entre dois usuários foi validado **estruturalmente** por RLS e permissões; **não foi provado comportamentalmente** porque há somente um usuário Auth e as tabelas estão vazias. Não criar usuário artificial neste banco CRM sem outra autorização.
- A publicação está `ACTIVE`, e os arquivos instalados foram conferidos. Uma chamada HTTP ao endpoint público para verificar `/health` e respostas 401 ainda não foi concluída pela ferramenta disponível. Não declarar esse teste aprovado.
- Avisos de segurança da auditoria do CRM (não `orq_`) foram identificados; fora do escopo e intocados.

## Próximas condições de aceite — SEM autorização neste turno
1. Teste comportamental RLS com dois usuários reais, sem tocar em usuários/tenants CRM indevidamente.
2. Pareamento de nó por sessão Auth legítima, guardando seu segredo somente no gerenciador do executor, nunca no repositório.
3. Aprovação **separada** para ativar o worker cloud na Railway, porque a autorização anterior a proíbe.
4. Executar uma única missão `diagnose` apenas em repo público permitido, com receipt, heartbeat e verificação, sem ações externas.
5. Merge e outras publicações seguem NÃO AUTORIZADOS.

Este arquivo é um **relato**, não é uma evidência de missão executada nem de serviço Railway operacional.
