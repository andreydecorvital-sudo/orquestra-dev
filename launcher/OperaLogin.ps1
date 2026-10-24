# Autenticacao ChatGPT/ Codex no Opera, sem alterar navegador padrao nem capturar tokens.
# Carregado pelo OrquestraMenu.ps1 depois de definir Has e Write-Event.

$script:CodexDeviceUrl = 'https://auth.openai.com/codex/device'

function Get-OperaPath {
  $configDir = if ($env:LOCALAPPDATA) { Join-Path $env:LOCALAPPDATA 'Orquestra' } else { Join-Path $env:USERPROFILE 'Orquestra' }
  $savedPath = Join-Path $configDir 'opera-path.txt'
  $paths = @()
  if ($env:ORQUESTRA_OPERA_PATH) { $paths += $env:ORQUESTRA_OPERA_PATH }
  if (Test-Path -LiteralPath $savedPath) {
    $paths += (Get-Content -LiteralPath $savedPath -Raw -ErrorAction SilentlyContinue).Trim()
  }
  foreach ($base in @($env:LOCALAPPDATA, $env:ProgramFiles, [Environment]::GetEnvironmentVariable('ProgramFiles(x86)'))) {
    if (-not $base) { continue }
    foreach ($relative in @(
      'Programs\Opera\opera.exe', 'Programs\Opera\launcher.exe',
      'Programs\Opera GX\opera.exe', 'Programs\Opera GX\launcher.exe',
      'Opera\opera.exe', 'Opera\launcher.exe',
      'Opera GX\opera.exe', 'Opera GX\launcher.exe'
    )) { $paths += (Join-Path $base $relative) }
  }
  foreach ($name in @('opera.exe','opera')) {
    $cmd = Get-Command $name -ErrorAction SilentlyContinue
    if ($cmd -and $cmd.Source) { $paths += $cmd.Source }
  }
  foreach ($candidate in $paths) {
    if ($candidate -and (Test-Path -LiteralPath $candidate -PathType Leaf) -and
        [IO.Path]::GetFileName($candidate).ToLowerInvariant() -in @('opera.exe','launcher.exe')) {
      return [string]$candidate
    }
  }
  Write-Host 'Nao localizei Opera ou Opera GX. Selecione o arquivo opera.exe / launcher.exe.' -ForegroundColor Yellow
  try {
    Add-Type -AssemblyName System.Windows.Forms
    $picker = New-Object System.Windows.Forms.OpenFileDialog
    $picker.Title = 'Selecione opera.exe ou launcher.exe do Opera'
    $picker.Filter = 'Opera (*.exe)|opera.exe;launcher.exe'
    $picker.CheckFileExists = $true
    if ($picker.ShowDialog() -ne [Windows.Forms.DialogResult]::OK) { return $null }
    $exe = $picker.FileName
    if ([IO.Path]::GetFileName($exe).ToLowerInvariant() -notin @('opera.exe','launcher.exe')) {
      Write-Host 'Selecione um executavel do Opera.' -ForegroundColor Yellow
      return $null
    }
    New-Item -ItemType Directory -Force -Path $configDir | Out-Null
    [IO.File]::WriteAllText($savedPath,$exe,[Text.UTF8Encoding]::new($false))
    return $exe
  } catch {
    Write-Host 'Nao foi possivel selecionar Opera. Nao abrirei o Chrome.' -ForegroundColor Yellow
    return $null
  }
}

function Open-OperaDeviceLogin([string]$operaExe) {
  if (-not $operaExe) { return $false }
  Start-Process -FilePath $operaExe -ArgumentList @($script:CodexDeviceUrl) -ErrorAction Stop
  Write-Host 'Pagina oficial ChatGPT/Codex aberta no Opera.' -ForegroundColor Cyan
  Write-Host 'O codigo de uso unico aparecera nesta janela. Digite-o no Opera.' -ForegroundColor Gray
  return $true
}


function Start-DeviceLoginConsole([string]$scriptFile) {
  $file = Join-Path $PSScriptRoot $scriptFile
  if (-not (Test-Path -LiteralPath $file -PathType Leaf)) {
    throw "Arquivo do iniciador ausente: $scriptFile. Extraia o ZIP completo atualizado."
  }
  # The OAuth CLI must run in a visible, real interactive console. Never capture
  # its stdout (the code is secret and needed directly by the account owner).
  $command = 'call "' + $file + '"'
  $process = Start-Process -FilePath 'cmd.exe' -ArgumentList @('/k', $command) -WorkingDirectory $PSScriptRoot -PassThru
  return ($null -ne $process)
}

function Prompt-AfterCode([string]$toolName,[string]$operaExe) {
  Write-Host ''
  Write-Host "Uma NOVA janela do CMD foi aberta para $toolName." -ForegroundColor Cyan
  Write-Host 'Aguarde ate ver o codigo de 9 caracteres naquela janela.' -ForegroundColor Gray
  Write-Host 'Se nao aparecer, leia a mensagem de erro que aparecer no CMD.' -ForegroundColor Gray
  $confirm = Read-Host 'O codigo apareceu na janela do CMD? (S/N)'
  if ($confirm -notmatch '^[sS]') {
    Write-Host 'Opera nao foi aberto: e necessario o Codex/Hermes gerar o codigo primeiro.' -ForegroundColor Yellow
    Write-Host 'Se houve erro, envie somente a mensagem do terminal, escondendo qualquer codigo ou token.' -ForegroundColor Gray
    Write-Event 'device_login' 'no_code'
    return $false
  }
  return (Open-OperaDeviceLogin -operaExe $operaExe)
}

function Login-CodexOpera {
  if (-not (Has 'codex')) { Write-Host 'Instale Codex primeiro.' -ForegroundColor Yellow; return }
  $opera = Get-OperaPath
  if (-not $opera) { Write-Event 'codex_login' 'opera_absent'; return }
  if (-not (Start-DeviceLoginConsole -scriptFile 'LOGIN-CODEX.cmd')) {
    Write-Event 'codex_login' 'console_failed'
    return
  }
  if (Prompt-AfterCode -toolName 'Codex' -operaExe $opera) {
    Write-Host 'Digite no Opera o codigo que aparece na NOVA janela do CMD.' -ForegroundColor Green
    Write-Host 'Apos autorizar, confira o resultado na janela do Codex.' -ForegroundColor Gray
    Write-Event 'codex_login' 'opera_opened'
  }
}

function Login-HermesOpera {
  if (-not (Has 'hermes')) { Write-Host 'Instale Hermes primeiro.' -ForegroundColor Yellow; return }
  $opera = Get-OperaPath
  if (-not $opera) { Write-Event 'hermes_login' 'opera_absent'; return }
  & hermes profile show nagi *> $null
  if ($LASTEXITCODE -ne 0) {
    & hermes profile create nagi
    if ($LASTEXITCODE -ne 0) { Write-Host 'Nao foi possivel criar o perfil Nagi.' -ForegroundColor Yellow; return }
  }
  # Hermes' documented default is device-code. Force it for this profile to
  # avoid opening the Windows default browser (Chrome) accidentally.
  & hermes -p nagi config set auth.codex_login_flow device_code
  if ($LASTEXITCODE -ne 0) {
    Write-Event 'hermes_login' 'device_config_failed'
    Write-Host 'Nao consegui selecionar login por codigo no Hermes.' -ForegroundColor Yellow
    return
  }
  if (-not (Start-DeviceLoginConsole -scriptFile 'LOGIN-HERMES.cmd')) {
    Write-Event 'hermes_login' 'console_failed'
    return
  }
  if (Prompt-AfterCode -toolName 'Hermes Nagi' -operaExe $opera) {
    Write-Host 'Digite no Opera o codigo que aparece na NOVA janela do CMD.' -ForegroundColor Green
    Write-Host 'Apos autorizar, confira o resultado na janela do Hermes.' -ForegroundColor Gray
    Write-Event 'hermes_login' 'opera_opened'
  }
}
