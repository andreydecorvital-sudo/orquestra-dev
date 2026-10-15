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

function Invoke-CodexDeviceLogin {
  & codex login --device-auth
  return $LASTEXITCODE
}

function Login-CodexOpera {
  if (-not (Has 'codex')) { Write-Host 'Instale Codex primeiro.' -ForegroundColor Yellow; return }
  $opera = Get-OperaPath
  if (-not $opera) { Write-Event 'codex_login' 'opera_absent'; return }
  if (-not (Open-OperaDeviceLogin -operaExe $opera)) { return }
  $result = Invoke-CodexDeviceLogin
  if ($result -ne 0) {
    Write-Event 'codex_login' 'failed'
    Write-Host 'Login nao concluido. Ative login por codigo de dispositivo nas configuracoes de seguranca do ChatGPT, se necessario.' -ForegroundColor Yellow
    Write-Host 'Nenhum Chrome ou API paga sera usado como fallback.' -ForegroundColor Yellow
  } else {
    Write-Event 'codex_login' 'ok'
    Write-Host 'Login Codex concluido.' -ForegroundColor Green
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
  # Force Hermes to use device login (browser/PKCE would open the Windows default).
  & hermes -p nagi config set auth.codex_login_flow device_code
  if ($LASTEXITCODE -ne 0) {
    Write-Event 'hermes_login' 'device_config_failed'
    Write-Host 'Nao consegui selecionar login por codigo. Parei para nao abrir Chrome.' -ForegroundColor Yellow
    return
  }
  if (-not (Open-OperaDeviceLogin -operaExe $opera)) { return }
  & hermes -p nagi auth add openai-codex --type oauth
  if ($LASTEXITCODE -ne 0) {
    Write-Event 'hermes_login' 'failed'
    Write-Host 'Login do Hermes nao concluido. Nenhuma chave de API paga foi utilizada.' -ForegroundColor Yellow
    return
  }
  Write-Event 'hermes_login' 'ok'
  Write-Host 'Login Hermes concluido. Escolha modelo Codex; a autenticacao pode ser reutilizada.' -ForegroundColor Green
  & hermes -p nagi model
}
