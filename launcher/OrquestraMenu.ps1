# Orquestra Windows launcher. Runs locally; never needs administrator permissions.
param([switch]$SelfTest)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$env:PYTHONIOENCODING = 'utf-8'

function Has([string]$name) { return [bool](Get-Command $name -ErrorAction SilentlyContinue) }
function Pause-Menu { [void](Read-Host 'Pressione ENTER para continuar') }
$script:RunLog = Join-Path $env:LOCALAPPDATA 'Orquestra\logs'
if (-not $env:LOCALAPPDATA) { $script:RunLog = Join-Path $env:USERPROFILE 'Orquestra\logs' }
try { New-Item -ItemType Directory -Force -Path $script:RunLog | Out-Null } catch { $script:RunLog = $null }
function Write-Event([string]$step,[string]$state) {
  # Log only known step names and exit codes; do NOT store prompt text or tokens.
  if (-not $script:RunLog) { return }
  $step = $step -replace '[^a-zA-Z0-9_-]','_'
  $state = $state -replace '[^a-zA-Z0-9_-]','_'
  try { Add-Content -LiteralPath (Join-Path $script:RunLog 'status.log') -Encoding UTF8 -Value "$(Get-Date -Format o) | $step | $state" } catch {}
}
. (Join-Path $PSScriptRoot 'OperaLogin.ps1')
function Submit-Mission([string]$mode,[string]$project,[string]$task) {
  Invoke-Orquestra -argsList @($mode,$project,$task)
}
function Header {
  Clear-Host
  Write-Host '====================================================' -ForegroundColor DarkGray
  Write-Host ' ORQUESTRA - CENTRAL DE AGENTES' -ForegroundColor Cyan
  Write-Host ' Gemini (Google) + Hermes + Codex (ChatGPT)' -ForegroundColor Gray
  Write-Host '====================================================' -ForegroundColor DarkGray
  Write-Host " Projetos: $env:ORQUESTRA_PROJECTS_HOME" -ForegroundColor DarkGray
  Write-Host ''
}
function Invoke-Orquestra([string[]]$argsList) {
  $operation = if ($argsList.Length -gt 0) { $argsList[0] } else { 'unknown' }
  Push-Location $root
  try {
    if (Has 'py') { & py -3 -m cli.orquestra @argsList }
    elseif (Has 'python') { & python -m cli.orquestra @argsList }
    else { Write-Host 'Python ausente. Selecione Configurar.' -ForegroundColor Yellow; Write-Event $operation 'python_missing'; return }
    if ($LASTEXITCODE -ne 0) { Write-Event $operation "exit_$LASTEXITCODE"; Write-Host "Comando falhou ($LASTEXITCODE). Veja o erro acima." -ForegroundColor Yellow }
    else { Write-Event $operation 'ok' }
  } finally { Pop-Location }
}
function Visit-Installer([string]$program,[string]$url) {
  $a = Read-Host "$program ausente. Abrir site oficial para instalar? (S/N)"
  if ($a -match '^[sS]') { Start-Process $url }
}
function Install-Npm([string]$app,[string]$package) {
  if (Has $app) { return }
  if (-not (Has 'npm.cmd')) { Write-Host "Instale Node.js antes de $app." -ForegroundColor Yellow; return }
  $a = Read-Host "Instalar $app via pacote oficial $package? (S/N)"
  if ($a -match '^[sS]') {
    & npm.cmd install -g $package
    if ($LASTEXITCODE -ne 0) { Write-Host "Erro na instalacao de $app." -ForegroundColor Yellow }
  }
}
function Clone-Missing {
  if (-not (Has 'git')) { return }
  $repos = @(
    @{id='origin';url='https://github.com/andreydecorvital-sudo/origin.git'},
    @{id='vitalhub';url='https://github.com/andreydecorvital-sudo/vitalhub.git'}
  )
  foreach ($repo in $repos) {
    $dest = Join-Path $env:ORQUESTRA_PROJECTS_HOME $repo.id
    if (Test-Path $dest) { Write-Host "Mantido sem alteracoes: $dest" -ForegroundColor Gray; continue }
    $a = Read-Host "Baixar $($repo.id) para $dest? (S/N)"
    if ($a -match '^[sS]') {
      New-Item -Type Directory -Path $env:ORQUESTRA_PROJECTS_HOME -Force | Out-Null
      & git clone $repo.url $dest
      if ($LASTEXITCODE -ne 0) { Write-Host 'Falha ao clonar. Pode exigir login no GitHub.' -ForegroundColor Yellow }
    }
  }
}
function Setup {
  Header
  foreach ($name in @('git','py','python','node','npm.cmd','hermes','codex','gemini')) {
    if (Has $name) { Write-Host "  OK: $name" -ForegroundColor Green }
    else { Write-Host "  Ausente: $name" -ForegroundColor Yellow }
  }
  Write-Host ''
  if (-not (Has 'git')) { Visit-Installer 'Git' 'https://git-scm.com/install/windows' }
  if ((-not (Has 'py')) -and (-not (Has 'python'))) {
    Visit-Installer 'Python' 'https://www.python.org/downloads/windows/'
  }
  if (-not (Has 'node')) { Visit-Installer 'Node.js LTS' 'https://nodejs.org/en/download' }
  if (-not (Has 'hermes')) { Visit-Installer 'Hermes Agent' 'https://hermes-agent.nousresearch.com/' }
  Install-Npm 'codex' '@openai/codex'
  Install-Npm 'gemini' '@google/gemini-cli'
  Clone-Missing
  if (Has 'hermes') { Invoke-Orquestra -argsList @('preparar') }
  Write-Host 'Se foi instalado algo agora, feche e reabra a Orquestra.' -ForegroundColor Yellow
  Pause-Menu
}
function Logins {
  Header
  Write-Host '1 - Entrar com ChatGPT no Codex (Opera)'
  Write-Host '2 - Entrar com conta Google no Gemini'
  Write-Host '3 - Conectar Hermes Nagi ao ChatGPT (Opera)'
  Write-Host '4 - Habilitar Codex runtime no Hermes Nagi'
  Write-Host '0 - Voltar'
  $opt = Read-Host 'Opcao'
  switch ($opt) {
    '1' { Login-CodexOpera }
    '2' {
      if (Has 'gemini') {
        Write-Host 'Selecione Sign in with Google. Saia do Gemini apos autenticar.' -ForegroundColor Gray
        & gemini
      } else { Write-Host 'Instale Gemini primeiro.' -ForegroundColor Yellow }
    }
    '3' { Login-HermesOpera }
    '4' {
      if ((Has 'hermes') -and (Has 'codex')) {
        Write-Host 'Abrindo Hermes Nagi para ativar o runtime oficial. Digite /codex-runtime codex_app_server e reinicie a sessao.' -ForegroundColor Gray
        & hermes -p nagi --tui
      } else { Write-Host 'Hermes e Codex sao necessarios.' -ForegroundColor Yellow }
    }
  }
  Pause-Menu
}
function Start-Motor {
  if (-not (Has 'hermes')) { Write-Host 'Instale Hermes em Configurar.' -ForegroundColor Yellow; return }
  Write-Host 'Abrindo Hermes em nova janela. Nao abra outra se ele ja esta rodando.' -ForegroundColor Cyan
  Start-Process -FilePath 'cmd.exe' -ArgumentList @('/k', 'title Hermes Gateway - Orquestra && hermes gateway start')
  Write-Host 'Deixe essa janela aberta enquanto executa tarefas.' -ForegroundColor Gray
}
function Mission {
  Header
  Write-Host '1 - Argoplace'
  Write-Host '2 - Origin'
  $proj = switch (Read-Host 'Projeto') { '1' {'argoplace'} '2' {'origin'} default {''} }
  if (-not $proj) { return }
  Write-Host '1 - Gemini planeja, Hermes delega, Codex investiga'
  Write-Host '2 - Hermes delega a investigacao direto ao Codex'
  $mode = switch (Read-Host 'Modo') { '1' {'equipe'} '2' {'investigar'} default {''} }
  if (-not $mode) { return }
  $task = Read-Host 'Descreva sua tarefa'
  if ([string]::IsNullOrWhiteSpace($task)) { return }
  if ($task.Length -gt 2500) { Write-Host 'Maximo de 2500 caracteres.' -ForegroundColor Yellow; Pause-Menu; return }
  Submit-Mission -mode $mode -project $proj -task $task
  Write-Host 'Use Acompanhar tarefas para consultar o resultado.' -ForegroundColor Cyan
  Pause-Menu
}
function Report {
  Header
  $outDir = if ($script:RunLog) { $script:RunLog } else { Join-Path $env:TEMP 'Orquestra' }
  New-Item -ItemType Directory -Path $outDir -Force | Out-Null
  $report = Join-Path $outDir 'diagnostico.txt'
  $rows = @('ORQUESTRA - Diagnostico local',('Criado em: ' + (Get-Date -Format o)),'')
  foreach ($name in @('git','python','py','node','npm.cmd','hermes','codex','gemini')) {
    $rows += ('Presente: ' + $name + '=' + [string](Has $name))
  }
  $rows += ''
  $rows += 'Ultimos eventos (sem prompts/tokens):'
  $log = Join-Path $outDir 'status.log'
  if (Test-Path $log) { $rows += @(Get-Content -LiteralPath $log -Tail 40) }
  $rows += ''
  $rows += 'Acoes: as informacoes deste arquivo nao incluem senhas nem logs brutos.'
  [IO.File]::WriteAllLines($report,$rows,[Text.UTF8Encoding]::new($false))
  Write-Host "Relatorio gerado: $report" -ForegroundColor Cyan
  $a = Read-Host 'Abrir relatorio no Bloco de Notas? (S/N)'
  if ($a -match '^[sS]') { Start-Process -FilePath 'notepad.exe' -ArgumentList ('"' + $report + '"') }
  Pause-Menu
}
function Board {
  Header
  Write-Host '1 - Consultar tarefas Argoplace'
  Write-Host '2 - Consultar tarefas Origin'
  Write-Host '3 - Abrir painel visual Kanban do Hermes'
  $opt = Read-Host 'Opcao'
  switch ($opt) {
    '1' { Invoke-Orquestra -argsList @('status','argoplace') }
    '2' { Invoke-Orquestra -argsList @('status','origin') }
    '3' {
      if (Has 'hermes') {
        Start-Process -FilePath 'cmd.exe' -ArgumentList @('/k', 'title Hermes Kanban - Orquestra && hermes dashboard')
        Write-Host 'Painel local: http://127.0.0.1:9119' -ForegroundColor Cyan
      } else { Write-Host 'Instale Hermes primeiro.' -ForegroundColor Yellow }
    }
  }
  Pause-Menu
}

if ($SelfTest) {
  $script:Forwarded = @()
  function Invoke-Orquestra([string[]]$argsList) { $script:Forwarded = @($argsList) }
  Submit-Mission -mode 'equipe' -project 'argoplace' -task 'Teste de tarefa com espaços'
  if ($script:Forwarded.Count -ne 3 -or $script:Forwarded[0] -ne 'equipe' -or
      $script:Forwarded[1] -ne 'argoplace' -or $script:Forwarded[2] -ne 'Teste de tarefa com espaços') {
    throw 'Falha no encaminhamento da missão do PowerShell para o Python'
  }
  Invoke-Orquestra -argsList @('status','origin')
  if ($script:Forwarded.Count -ne 2 -or $script:Forwarded[1] -ne 'origin') {
    throw 'Falha no encaminhamento do status de projeto'
  }
  # Verify that login flow selects an Opera binary and device auth without launching any browser.
  $script:FakeOperaOpened = $null
  $script:FakeCodexInvoked = $false
  function Get-OperaPath { return 'C:\TestOpera\opera.exe' }
  function Open-OperaDeviceLogin([string]$operaExe) {
    $script:FakeOperaOpened = $operaExe
    return $true
  }
  function Invoke-CodexDeviceLogin {
    $script:FakeCodexInvoked = $true
    return 0
  }
  function Has([string]$name) { return $true }
  Login-CodexOpera
  if (-not $script:FakeCodexInvoked -or
      $script:FakeOperaOpened -ne 'C:\TestOpera\opera.exe') {
    throw 'Falha no login Codex via Opera'
  }
  Write-Host 'OK: encaminhamento das tarefas, status e login Opera/Codex'
  exit 0
}
if ($env:ORQUESTRA_PROJECTS_HOME) {

  $env:ORQUESTRA_PROJECTS_HOME = [System.IO.Path]::GetFullPath($env:ORQUESTRA_PROJECTS_HOME)
} elseif ((Test-Path (Join-Path (Split-Path -Parent $root) 'origin\.git')) -or
          (Test-Path (Join-Path (Split-Path -Parent $root) 'vitalhub\.git'))) {
  $env:ORQUESTRA_PROJECTS_HOME = Split-Path -Parent $root
} else {
  $env:ORQUESTRA_PROJECTS_HOME = Join-Path $env:USERPROFILE 'Projetos'
}
while ($true) {
  try {
    Header
    Write-Host '1 - Configurar instalacao (uma vez)'
    Write-Host '2 - Conectar contas (uma vez)'
    Write-Host '3 - Iniciar motor Hermes'
    Write-Host '4 - Nova missao'
    Write-Host '5 - Acompanhar / Painel Kanban'
    Write-Host '6 - Diagnostico'
    Write-Host '7 - Salvar relatorio de erros'
    Write-Host '0 - Sair'
    $choice = Read-Host 'Escolha'
    switch ($choice) {
      '1' { Setup }
      '2' { Logins }
      '3' { Start-Motor; Pause-Menu }
      '4' { Mission }
      '5' { Board }
      '6' { Header; Invoke-Orquestra -argsList @('doctor'); Pause-Menu }
      '7' { Report }
      '0' { break }
      default { Write-Host 'Opcao invalida.' -ForegroundColor Yellow; Pause-Menu }
    }
    if ($choice -eq '0') { break }
  } catch {
    Write-Event 'menu' $_.Exception.GetType().Name
    Write-Host ('Erro: ' + $_.Exception.Message) -ForegroundColor Red
    Write-Host 'Use a opcao 7 para abrir o relatorio de diagnostico.' -ForegroundColor Yellow
    Pause-Menu
  }
}
