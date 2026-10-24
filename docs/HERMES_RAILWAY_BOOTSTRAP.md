# Hermes na Railway: plano de implantação com autenticação ChatGPT/Codex

## Escopo e estado

Este procedimento **não foi executado**. Não há serviço Railway da Orquestra, OAuth Hermes realizado, worker remoto validado ou conexão com a Argoplace. O PR #18 atual entrega um contêiner de **diagnóstico sem Hermes instalado**. Este documento define os próximos gates e NÃO autoriza provisionamento, custo, deploy ou merge.

Fonte do runtime: documentação oficial https://hermes-agent.nousresearch.com/docs/user-guide/docker
Fonte OAuth: https://hermes-agent.nousresearch.com/docs/integrations/providers
Fonte controle de gastos: https://docs.railway.com/pricing/cost-control

## Reutilizar a assinatura Railway existente (19/10/2026)

A conta conectada já possui o workspace pessoal `andreydecorvital-sudo's Projects` (três projetos: `argoplace-whatsapp`, `argoplace-shopee-gateway` e `ned-marketing-live`). **Não contratar outro plano Railway.** Um projeto `orquestra-cloud` pode ser criado **nesse mesmo workspace** depois da aprovação de infraestrutura; projetos separados facilitam isolamento de segredos, deploy e permissões. Não tocar nos workloads ativos WAHA/Shopee e não reaproveitar seus volumes.

A mesma assinatura não torna o novo executor gratuito. Railway cobra recursos consumidos pelo conjunto de serviços. Primeiro consultar `Workspace → Usage` para ver o gasto atual e a margem de crédito incluída no plano; este conector não confirmou o tipo de plano nem o valor exato da fatura. O piloto começa com somente **um serviço** e um volume pequeno exclusivo de autenticação; não iniciar dois executores 24/7 sem evidência de necessidade.

**Atenção ao limite rígido:** o teto de computação Railway se aplica ao workspace completo. Se for atingido, a plataforma desliga também os serviços WAHA e Shopee. Para controlar custos sem interromper a Argoplace, preferir alerta por e-mail e limites de recursos do serviço; não alterar hard limit do workspace sem aprovação explícita dos riscos. Nunca ajustar limites de produção em nome do teste.

Fonte de preços: https://docs.railway.com/pricing
Fonte de controles de gasto: https://docs.railway.com/pricing/cost-control

## Etapa A — Hermes independente (antes de integrar a Orquestra)

1. Obter aprovação de custo e de criação do projeto Railway `orquestra-cloud`. Definir aviso e limite rígido de gasto no workspace. Não reutilizar os serviços Railway do Argoplace.
2. Criar **serviço privado**, sem domínio público, a partir da imagem Docker oficial do Hermes, fixando uma versão/digest verificada depois de avaliação de origem e supply-chain. Evitar `latest` em operação contínua.
3. Anexar volume privado persistente em `/opt/data` (local oficial de estado do Hermes). Testar permissões, reinício e acesso exclusivo da instância; nunca colocar OAuth em variáveis públicas, no Git, na Vercel ou no Supabase.
4. Usar terminal privado da instância (quando disponível) para iniciar `hermes auth add openai-codex`. O fluxo padrão permite código de dispositivo: o titular entra somente no site de autorização que o Hermes exibir e aprova com sua própria conta ChatGPT. Se device code estiver bloqueado, usar o fluxo OAuth browser/PKCE suportado e acesso remoto seguro ao callback local — nunca copiar credenciais/cookies para este chat.
5. Usar `hermes model` e selecionar *ChatGPT or Codex Subscription*. Desabilitar provedores de fallback pagos, modelos auxiliares cobrados e `auth.adopt_external_logins`. Confirmar que o provedor em uso é `openai-codex`.
6. Rodar `hermes auth status openai-codex` e `hermes usage --provider openai-codex --json`. Registrar somente estado redigido de conexão; não registrar saída bruta, usuário, percentuais de cota ou tokens em logs centralizados.
7. Só após checagem de segurança, uma **única** conversa de teste simples e explícita: `hermes chat -q "Responda somente: ORQUESTRA OK"`. Confirmar resultado, uso e mensagens de erro sem dados sensíveis. Isso comprova inferência **do Hermes**, não execução de código da Orquestra.
8. Reiniciar a instância e confirmar sessão válida e protegida pelo volume, sem nova exportação de tokens. Em falha de quota/revogação, parar sem fallback pago.

## Etapa B — Conectar à Orquestra

O atual `gateway/hermes_bridge.py` só aceita `127.0.0.1:8642` e lê um arquivo local Hermes. Um serviço Railway independente NÃO fica acessível por localhost de outro serviço. Não basta apontar `localhost` para outra instância.

Antes de conectar a API, implementar e revisar **uma** topologia autorizada:

- Hermes e worker no mesmo contêiner/workload isolado, conversando por loopback (preferencial para o primeiro piloto); ou
- Hermes numa rede privada com adaptador específico, autenticação mútua e allowlist de destino, mantendo API e tokens fora da internet.

Não publicar porta 8642 em domínio aberto. Evitar CORS amplo. Manter ferramentas do perfil API do Hermes desativadas para planejamento textual durante o primeiro piloto. O uso de login Hermes **não** autentica a CLI Codex separada. O executor de código continuará sem permissão até integração, isolamento e verificação próprios.

## Etapa C — Fila, banco e Argoplace

O painel Vercel é existente, mas a conexão Supabase autorizada neste chat só enxerga um projeto operacional que não deve ser usado como fallback. Confirmar acesso ao **projeto Supabase exclusivo da Orquestra**, banco e migrações antes de registrar device e tarefas. Não inventar projeto, credencial ou permissão.

Com o backend correto:
- Missão `diagnose` no repositório público de teste e prova de claim/heartbeat/complete.
- Missão Hermes de planejamento **sem ferramentas** e resposta comprovada.
- Só depois disponibilizar clone autorizado de `vitalhub` em sandbox, com testes e revisão de patches.
- Deploy, merge, preços, emissão fiscal, impressão e ações reais de marketplace seguem aprovação humana específica.

## Critério de conclusão

Reportar separadamente `image_ready`, `host_ready`, `oauth_authenticated`, `inference_verified`, `orquestra_connected` e `argoplace_safe_pilot_verified`. Nenhum desses estados deve ser inferido de README, CI ou sucesso HTTP do painel. Limites da assinatura e da nuvem não autorizam automação ilimitada.
