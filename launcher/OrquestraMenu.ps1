# Orquestra Windows launcher. Runs locally; never needs administrator permissions.
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$env:PYTHONIOENCODING = 'utf-8'

function Has([string]$name) { return [bool](Get-Command $name -ErrorAction SilentlyContinue) }
function Pause-Menu { [void](Read-Host 'Pressione ENTER para continuar') }
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
  Push-Location $root
  try {
    if (Has 'py') { & py -3 -m cli.orquestra @argsList }
    elseif (Has 'python') { & python -m cli.orquestra @argsList }
    else { Write-Host 'Python ausente. Selecione Configurar.' -ForegroundColor Yellow; return }
    if ($LASTEXITCODE -ne 0) { Write-Host "Comando falhou ($LASTEXITCODE). Veja o erro acima." -ForegroundColor Yellow }
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
  if (Has 'hermes') { Invoke-Orquestra @('preparar') }
  Write-Host 'Se foi instalado algo agora, feche e reabra a Orquestra.' -ForegroundColor Yellow
  Pause-Menu
}
function Logins {
  Header
  Write-Host '1 - Entrar com ChatGPT no Codex'
  Write-Host '2 - Entrar com conta Google no Gemini'
  Write-Host '3 - Configurar login ChatGPT/Codex do Hermes Nagi'
  Write-Host '4 - Habilitar Codex runtime no Hermes Nagi'
  Write-Host '0 - Voltar'
  $opt = Read-Host 'Opcao'
  switch ($opt) {
    '1' {
      if (Has 'codex') { & codex login }
      else { Write-Host 'Instale Codex primeiro.' -ForegroundColor Yellow }
    }
    '2' {
      if (Has 'gemini') {
        Write-Host 'Selecione Sign in with Google. Saia do Gemini apos autenticar.' -ForegroundColor Gray
        & gemini
      } else { Write-Host 'Instale Gemini primeiro.' -ForegroundColor Yellow }
    }
    '3' {
      if (Has 'hermes') {
        & hermes profile show nagi *> $null
        if ($LASTEXITCODE -ne 0) { & hermes profile create nagi }
        & hermes -p nagi model
      } else { Write-Host 'Instale Hermes primeiro.' -ForegroundColor Yellow }
    }
    '4' {
      if ((Has 'hermes') -and (Has 'codex')) {
        Write-Host 'Isso atualiza config local e migra ferramentas Codex do Nagi.' -ForegroundColor Gray
        $ok = Read-Host 'Autoriza ativar o runtime? (S/N)'
        if ($ok -match '^[sS]') {
          & hermes -p nagi config set model.openai_runtime codex_app_server
          if ($LASTEXITCODE -eq 0) { & hermes -p nagi codex-runtime migrate }
        }
      } else { Write-Host 'Hermes e Codex sao necessarios.' -ForegroundColor Yellow }
    }
  }
  Pause-Menu
}
function Start-Motor {
  if (-not (Has 'hermes')) { Write-Host 'Instale Hermes em Configurar.' -ForegroundColor Yellow; return }
  Write-Host 'Abrindo Hermes em nova janela. Nao abra outra se ele ja esta rodando.' -ForegroundColor Cyan
  Start-Process -FilePath 'cmd.exe' -ArgumentList @('/k', 'title Hermes Gateway - Orquestra && hermes gateway')
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
  Invoke-Orquestra @($mode,$proj,$task)
  Write-Host 'Use Acompanhar tarefas para consultar o resultado.' -ForegroundColor Cyan
  Pause-Menu
}
function Board {
  Header
  Write-Host '1 - Consultar tarefas Argoplace'
  Write-Host '2 - Consultar tarefas Origin'
  Write-Host '3 - Abrir painel visual Kanban do Hermes'
  $opt = Read-Host 'Opcao'
  switch ($opt) {
    '1' { Invoke-Orquestra @('status','argoplace') }
    '2' { Invoke-Orquestra @('status','origin') }
    '3' {
      if (Has 'hermes') {
        Start-Process -FilePath 'cmd.exe' -ArgumentList @('/k', 'title Hermes Kanban - Orquestra && hermes dashboard')
        Write-Host 'Painel local: http://127.0.0.1:9119' -ForegroundColor Cyan
      } else { Write-Host 'Instale Hermes primeiro.' -ForegroundColor Yellow }
    }
  }
  Pause-Menu
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
    Write-Host '0 - Sair'
    $choice = Read-Host 'Escolha'
    switch ($choice) {
      '1' { Setup }
      '2' { Logins }
      '3' { Start-Motor; Pause-Menu }
      '4' { Mission }
      '5' { Board }
      '6' { Header; Invoke-Orquestra @('doctor'); Pause-Menu }
      '0' { break }
      default { Write-Host 'Opcao invalida.' -ForegroundColor Yellow; Pause-Menu }
    }
    if ($choice -eq '0') { break }
  } catch {
    Write-Host ('Erro: ' + $_.Exception.Message) -ForegroundColor Red
    Pause-Menu
  }
}
