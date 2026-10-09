# Orquestra — Primeiro acesso e pareamento (v1.1)

## 1. Login privado no painel

O projeto Supabase **orquestra-dev** já existe na região \`sa-east-1\`.
A UI em https://orquestra-dev-app.vercel.app/ usa somente \`sb_publishable_\` pública.

A integração Supabase disponível não possui ação segura de criação de usuários
Auth. O titular da conta deve ir em
[Authentication → Users](https://supabase.com/dashboard/project/kekxcvcgyexcbleifffq/auth/users),
usar **Add user → Create new user**, definir o seu próprio e-mail/senha e
entrar na Orquestra. **Não encaminhar senhas ou links de convite neste chat**.

Depois do primeiro cadastro, nas configurações de Auth no Supabase, desative
novos cadastros públicos; use convites individuais para colaboradores.
Verifique o site URL e os redirects de Auth se habilitar e-mail de convite ou
recuperação de senha. A interface NÃO implementa inscrição pública.

## 2. Cadastrar um repositório de sandbox

No painel, crie um projeto com URL GitHub pública **sem segredos**. No Windows,
tenha um clone local desse mesmo repositório e note o caminho absoluto. Não
autorize, neste primeiro piloto, o Argoplace/CRM em produção.

## 3. Parear executor Windows

Abra **Executores** no painel já autenticado. Informe um nome, selecione o
projeto e preencha a pasta Git exata no Windows. Ao clicar em **Parear**,
faça download do arquivo \`orquestra-agent-worker.json\`.

Na máquina Windows, abra PowerShell dentro de um clone de \`orquestra-dev\`:

\`\`\`powershell
git clone https://github.com/andreydecorvital-sudo/orquestra-dev.git
cd orquestra-dev
powershell -NoProfile -File .\runner\setup-windows.ps1 -ConfigFile "$env:USERPROFILE\Downloads\orquestra-agent-worker.json"
python -m runner.agent_worker
\`\`\`

O instalador valida o projeto, ID de dispositivo, segredo e pasta Git; instala
o arquivo em \`runner/agent-worker.json\` com ACL restrita ao usuário Windows.
A execução começa só em modo **diagnóstico**, sem chamar IA.
Se a política do Windows bloquear PowerShell, utilize uma instalação aprovada
pelo administrador em vez de baixar scripts desconhecidos ou desativar
proteções globalmente.

## 4. Habilitar agentes pelas assinaturas

1. Faça \`codex login\` e \`claude\` (login na CLI oficial) no computador do executor.
2. Verifique \`codex login status\` e \`claude auth status\`.
3. Em \`runner/agent-worker.json\` (privado, ignorado pelo Git), marque
   \`"allow_execution": true\` **apenas após o teste diagnóstico**.
4. Rode \`python -m runner.agent_worker\`. As capacidades anunciam apenas
   provedores autenticados. Nenhum fallback automático para APIs pagas.
5. Acompanhe o primeiro relatório em Missões.

## Limitações reais

- Sem usuário Auth, não existe login nem criação de projetos e executor na UI.
- Sem worker ligado, a fila persiste mas ninguém executa o trabalho.
- No notebook desligado, não existe execução 24/7. Exige executor na nuvem
  com login oficial autorizado e um serviço operacionalmente persistente.
- O resultado é um patch Git local para revisão, **não um PR publicado**.
- Não foram configurados envio de e-mail, provedores de login social,
  instalações CLI remotas nem credenciais de terceiros.
