# Hermes → ChatGPT/Codex: autenticação da Orquestra Cloud

## Decisão

A Orquestra Cloud deve preferir **Hermes Agent com o provedor `openai-codex` e autenticação OAuth da conta ChatGPT do titular**, usando os recursos de assinatura para os quais ele for elegível, antes de considerar alternativas de inferência. Isso **não** significa que Hermes já está instalado no executor cloud, conectado a qualquer conta ou habilitado para executar código. O piloto atual do PR #18 permanece restrito a diagnóstico, sem IA.

A interface web não autentica em nome do usuário: ela somente informa os estados `not_configured`, `authorization_required`, `authenticated`, `rate_limited`, `unavailable` ou `tested`, derivados de verificações reais do executor. Os tokens nunca chegam ao navegador, ao GitHub, ao Supabase ou ao modelo.

## Primeiro login, com consentimento humano

A autenticação precisa acontecer **dentro do ambiente isolado e persistente do Hermes**, por operador autorizado, após Hermes ter sido instalado e revisado. Para um host sem navegador, preferir o device code suportado pela ferramenta quando permitido pelo workspace:

    hermes auth add openai-codex
    hermes auth status openai-codex
    hermes model
    hermes usage --provider openai-codex --json

Em `hermes model`, escolher **ChatGPT or Codex Subscription** e verificar `model.provider: openai-codex`. A CLI pode solicitar que o usuário abra uma página oficial e confirme um código. Isso é **autorização interativa inicial**, não contorno de autenticação e não requer enviar senha ao chat.

Quando o device-code estiver bloqueado no workspace, seguir o fluxo browser + PKCE documentado:

    hermes auth add openai-codex --browser

Esse modo recebe um callback no `localhost:1455` **da própria máquina que executa Hermes**. Em servidor remoto, a autorização só pode ser concluída por um mecanismo de encaminhamento/túnel de localhost suportado, revisto e aprovado, sem interceptar OAuth; caso contrário, manter a missão bloqueada. Nunca usar URL de callback, cookies ou refresh tokens colados em prompts para improvisar a autenticação.

## Sessões e operação

- A conta é do titular que autorizou, com escopo e elegibilidade real do plano; quotas e termos aplicam-se normalmente. Não prometer agentes ilimitados nem uso irrestrito da Responses API.
- O Hermes possui estado OAuth próprio (p. ex. `~/.hermes/auth.json`). **Isso não faz login automaticamente no Codex CLI**: caso a Orquestra invoque `codex exec` separadamente, esse runtime terá de validar sua própria autenticação oficial ou a missão será bloqueada.
- Guardar o estado Hermes somente num volume privado/persistente da instância cloud, com permissões restritas e proteções adequadas; nunca embutir OAuth no contêiner ou no Git e não exibir credenciais em logs.
- Configurar `auth.adopt_external_logins: false` para não importar/atualizar arquivos de sessões do Codex CLI inadvertidamente, evitando disputa de refresh tokens.
- Não usar fallback para `OPENAI_API_KEY`, OpenRouter, Nous ou outro provedor cobrado sem consentimento financeiro específico. Desabilitar `fallback_providers` e modelos auxiliares cobrados quando se usar o perfil subscription-only.
- Avaliar a segurança e as licenças do Hermes antes da instalação e usar APIs/fluxos documentados; não imitar aplicações oficiais nem contornar quotas.
- Em `429`, falha de refresh, permissão negada ou revogação, pausar a missão e informar o bloqueio com evidências redigidas. Reautenticação sempre conduzida pelo titular.
- No primeiro marco, Hermes opera somente como **planejador/revisor textual sem ferramentas habilitadas**, conforme `gateway/hermes_bridge.py`. Habilitar escrita no worktree seria outra etapa: exigiria adaptador confiável, sandbox, testes e autorização.
- Nenhuma sessão autenticada deve ser compartilhada entre tenants ou usuários. Uso na nuvem não depende de PC ligado **depois** da implantação do executor persistente.

## Teste não interativo de prontidão — sem autenticar nem gastar tokens

No executor **que efetivamente tiver Hermes instalado e autorizado**, execute:

    python -m cloud.hermes_smoke

A checagem só usa comandos oficiais `hermes config get ... --json` e `hermes usage --provider openai-codex --json`. Consulta o status de uso **apenas depois** de confirmar `model.provider=openai-codex`, ausência de `fallback_providers` e `auxiliary`, `auth.adopt_external_logins=false` e ausência de variáveis de API paga no ambiente. Nunca imprime stdout/stderr do Hermes, uso por janela, IDs nem segredos.

`subscription_usage_verified` significa apenas que o CLI autenticado retornou o relatório de uso. **Não comprova que uma inferência funcionou** ou que o serviço remoto está disponível. `hermes_not_installed` significa que ainda não há runtime instalado; `usage_probe_unavailable` pede investigação local segura sem autenticação automática.

O contêiner inicial do PR #18 não instala Hermes, portanto esse teste nele retorna `hermes_not_installed`. Depois da revisão de suprimentos, instalação em contêiner separado e OAuth com consentimento explícito, a mesma verificação vira o primeiro gate para ativar planejamento textual controlado.

## Critérios de aceite do marco Hermes Cloud

1. Contêiner cloud do Hermes instalado a partir de artefatos revisados, isolado do worker de produção e da Argoplace.
2. OAuth `openai-codex` concluído pelo usuário, armazenado somente na instância cloud autorizada.
3. Provedor, modelos e quotas verificados sem expor tokens.
4. Solicitação de planejamento real com resposta registrada, **sem ferramentas externas ativadas**, sem API key cobrada e com timeout limitado.
5. Reinicialização controlada comprovando persistência segura da sessão; revogação e fim da quota testados com falha segura.
6. Só depois integrar os estágios de implementação/verificação de código e testar missão completa num repositório de sandbox.

## Referências

- Hermes: https://hermes-agent.nousresearch.com/docs/integrations/providers
- Hermes auth: https://hermes-agent.nousresearch.com/docs/reference/cli-commands
- Hermes segurança/borrowed logins: https://hermes-agent.nousresearch.com/docs/user-guide/security
- Codex com ChatGPT: https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan

**Estado em 19/10/2026:** requisito documentado; OAuth não realizado, Hermes cloud não implantado, sem custos adicionais autorizados.
