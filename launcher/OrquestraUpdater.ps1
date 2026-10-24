# Orquestra self-updater for Windows PowerShell 5.1+.
# Checks the public GitHub development channel on each launch. No GitHub token required.
param(
  [switch]$Quiet,
  [switch]$Force,
  [switch]$SelfTest
)
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 } catch {}

$script:Owner = 'andreydecorvital-sudo'
$script:Repository = 'orquestra-dev'
$script:Branch = 'feat/hermes-kanban-orquestra-cli-20261015'
$script:InstallRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$script:StateHome = if ($env:LOCALAPPDATA) {
  Join-Path $env:LOCALAPPDATA 'Orquestra'
} else {
  Join-Path $env:USERPROFILE 'Orquestra'
}
$script:LogHome = Join-Path $script:StateHome 'logs'
$script:UpdateLog = Join-Path $script:LogHome 'updater.log'
$script:NoticeFile = Join-Path $script:StateHome 'update-notice.txt'

function Write-UpdateLog([string]$Message) {
  try {
    New-Item -ItemType Directory -Force -Path $script:LogHome | Out-Null
    $safe = ($Message -replace '[\r\n|]', ' ').Trim()
    Add-Content -LiteralPath $script:UpdateLog -Encoding UTF8 -Value "$(Get-Date -Format o) | $safe"
    $lines = @(Get-Content -LiteralPath $script:UpdateLog -Tail 200 -ErrorAction SilentlyContinue)
    [IO.File]::WriteAllLines($script:UpdateLog, $lines, [Text.UTF8Encoding]::new($false))
  } catch {}
}

function Get-InstallKey([string]$Path) {
  $normalized = [IO.Path]::GetFullPath($Path).ToLowerInvariant()
  $sha = [Security.Cryptography.SHA256]::Create()
  try {
    $bytes = $sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($normalized))
    return ([BitConverter]::ToString($bytes)).Replace('-', '').Substring(0, 16)
  } finally { $sha.Dispose() }
}

function Get-StateFile {
  $key = Get-InstallKey $script:InstallRoot
  return (Join-Path $script:StateHome ("update-state-" + $key + ".json"))
}

function Read-UpdateState([string]$StateFile) {
  if (-not (Test-Path -LiteralPath $StateFile -PathType Leaf)) { return $null }
  try { return (Get-Content -LiteralPath $StateFile -Raw -Encoding UTF8 | ConvertFrom-Json) }
  catch { return $null }
}

function Write-UpdateNotice([string]$Message) {
  try {
    New-Item -ItemType Directory -Force -Path $script:StateHome | Out-Null
    [IO.File]::WriteAllText($script:NoticeFile, $Message, [Text.UTF8Encoding]::new($false))
  } catch {}
}

function Test-ExcludedUpdatePath([string]$RelativePath) {
  $normalized = $RelativePath.Replace('/', '\')
  $parts = $normalized.Split([char]92)
  $excludedDirectories = @('.git','.venv','venv','node_modules','__pycache__','.pytest_cache','.mypy_cache','data','logs','projects','dist','build')
  foreach ($part in $parts) {
    if ($excludedDirectories -contains $part) { return $true }
  }
  $name = [IO.Path]::GetFileName($normalized)
  if ($normalized -eq 'ABRIR-ORQUESTRA.cmd') { return $true } # bootstrap batch file is executing the updater
  if ($name -eq '.env' -or ($name -match '^\.env\.' -and $name -notin @('.env.example','.env.sample','.env.template'))) { return $true }
  if ($name -match '\.(log|sqlite|sqlite3|db|pyc|pem|p12)$') { return $true }
  if ($normalized -match '(^|\\)runner\\agent-worker\.json$') { return $true }
  if ($normalized -match '(^|\\)gateway\\config\.json$') { return $true }
  if ($normalized -match '(^|\\)web\\config\.js$') { return $true }
  return $false
}

function Copy-UpdateFiles([string]$SourceRoot, [string]$TargetRoot) {
  $sourceFull = [IO.Path]::GetFullPath($SourceRoot)
  $sourcePrefix = $sourceFull
  if (-not $sourcePrefix.EndsWith('\')) { $sourcePrefix += '\' }
  $sourceUri = [System.Uri]$sourcePrefix
  $targetFull = [IO.Path]::GetFullPath($TargetRoot)
  if (-not (Test-Path -LiteralPath $targetFull -PathType Container)) {
    New-Item -ItemType Directory -Force -Path $targetFull | Out-Null
  }
  $backupRoot = Join-Path $env:TEMP ("Orquestra-update-backup-" + [guid]::NewGuid().ToString('N'))
  $changes = New-Object System.Collections.ArrayList
  try {
    $sourceFiles = @(Get-ChildItem -LiteralPath $sourceFull -File -Recurse -Force)
    if ($sourceFiles.Count -eq 0) { throw 'O pacote de atualização não contém arquivos.' }
    foreach ($file in $sourceFiles) {
      $relativeUri = $sourceUri.MakeRelativeUri([System.Uri]$file.FullName)
      $relative = [System.Uri]::UnescapeDataString($relativeUri.ToString()).Replace('/', '\')
      if (Test-ExcludedUpdatePath $relative) { continue }
      $destination = Join-Path $targetFull $relative
      if (Test-Path -LiteralPath $destination -PathType Container) {
        throw ("Conflito: existe uma pasta no lugar do arquivo " + $relative)
      }
      $parent = Split-Path -Parent $destination
      New-Item -ItemType Directory -Force -Path $parent | Out-Null
      $existed = Test-Path -LiteralPath $destination -PathType Leaf
      $backup = $null
      if ($existed) {
        $backup = Join-Path $backupRoot $relative
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $backup) | Out-Null
        Copy-Item -LiteralPath $destination -Destination $backup -Force
      }
      $entry = [pscustomobject]@{ Destination = $destination; Backup = $backup; Existed = $existed }
      [void]$changes.Add($entry)
      Copy-Item -LiteralPath $file.FullName -Destination $destination -Force
    }
  } catch {
    for ($i = $changes.Count - 1; $i -ge 0; $i--) {
      $entry = $changes[$i]
      try {
        if ($entry.Existed -and $entry.Backup -and (Test-Path -LiteralPath $entry.Backup -PathType Leaf)) {
          Copy-Item -LiteralPath $entry.Backup -Destination $entry.Destination -Force
        } elseif (-not $entry.Existed -and (Test-Path -LiteralPath $entry.Destination -PathType Leaf)) {
          Remove-Item -LiteralPath $entry.Destination -Force
        }
      } catch {}
    }
    throw
  } finally {
    if (Test-Path -LiteralPath $backupRoot) {
      Remove-Item -LiteralPath $backupRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
  }
}

function Get-RemoteCommit {
  $escapedBranch = [Uri]::EscapeDataString($script:Branch)
  $api = "https://api.github.com/repos/$($script:Owner)/$($script:Repository)/commits?sha=$escapedBranch&per_page=1"
  $headers = @{
    Accept = 'application/vnd.github+json'
    'User-Agent' = 'Orquestra-Windows-Updater'
    'X-GitHub-Api-Version' = '2022-11-28'
  }
  $response = Invoke-RestMethod -Method Get -Uri $api -Headers $headers -TimeoutSec 15
  if ($response -is [array]) {
    if ($response.Count -lt 1) { throw 'O GitHub não retornou commits para o canal configurado.' }
    $commit = [string]$response[0].sha
  } else {
    $commit = [string]$response.sha
  }
  if ($commit -notmatch '^[0-9a-f]{40}$') { throw 'O GitHub retornou um identificador de versão inválido.' }
  return $commit
}

function Invoke-SelfTest {
  $testRoot = Join-Path $env:TEMP ("Orquestra-updater-selftest-" + [guid]::NewGuid().ToString('N'))
  $source = Join-Path $testRoot 'source'
  $target = Join-Path $testRoot 'install'
  try {
    New-Item -ItemType Directory -Force -Path (Join-Path $source 'launcher'), (Join-Path $source 'logs'), (Join-Path $target 'launcher'), (Join-Path $target 'logs') | Out-Null
    Set-Content -LiteralPath (Join-Path $source 'launcher\OrquestraMenu.ps1') -Value 'new-version' -Encoding UTF8
    Set-Content -LiteralPath (Join-Path $source '.env') -Value 'new-secret-must-not-copy' -Encoding UTF8
    Set-Content -LiteralPath (Join-Path $source 'logs\app.log') -Value 'new-log-must-not-copy' -Encoding UTF8
    Set-Content -LiteralPath (Join-Path $target 'launcher\OrquestraMenu.ps1') -Value 'old-version' -Encoding UTF8
    Set-Content -LiteralPath (Join-Path $target '.env') -Value 'keep-local-secret' -Encoding UTF8
    Set-Content -LiteralPath (Join-Path $target 'logs\app.log') -Value 'keep-local-log' -Encoding UTF8
    Copy-UpdateFiles -SourceRoot $source -TargetRoot $target
    if ((Get-Content -LiteralPath (Join-Path $target 'launcher\OrquestraMenu.ps1') -Raw).Trim() -ne 'new-version') {
      throw ('O self-test não atualizou o arquivo de aplicação. Conteúdo=' + (Get-Content -LiteralPath (Join-Path $target 'launcher\OrquestraMenu.ps1') -Raw) + '; arquivos=' + ((Get-ChildItem -LiteralPath $target -Recurse -File | ForEach-Object { $_.FullName }) -join ', '))
    }
    if ((Get-Content -LiteralPath (Join-Path $target '.env') -Raw).Trim() -ne 'keep-local-secret') {
      throw 'O self-test detectou alteração indevida de .env local.'
    }
    if ((Get-Content -LiteralPath (Join-Path $target 'logs\app.log') -Raw).Trim() -ne 'keep-local-log') {
      throw 'O self-test detectou alteração indevida de logs locais.'
    }
    Write-Host 'OK: updater atualiza arquivos do app e preserva .env/logs locais.'
  } finally {
    if (Test-Path -LiteralPath $testRoot) { Remove-Item -LiteralPath $testRoot -Recurse -Force -ErrorAction SilentlyContinue }
  }
}

if ($SelfTest) {
  Invoke-SelfTest
  exit 0
}

$tempRoot = $null
$exitCode = 0
try {
  New-Item -ItemType Directory -Force -Path $script:StateHome | Out-Null
  $stateFile = Get-StateFile
  $state = Read-UpdateState $stateFile
  $remoteCommit = Get-RemoteCommit
  $localCommit = if ($state -and $state.branch -eq $script:Branch) { [string]$state.commit } else { '' }

  if (-not $Force -and $localCommit -eq $remoteCommit) {
    if (-not $Quiet) { Write-Host ("Orquestra já está atualizada (" + $remoteCommit.Substring(0,7) + ").") -ForegroundColor Green }
    exit 0
  }

  if (-not $Quiet) {
    Write-Host 'Nova versão da Orquestra encontrada. Baixando atualização...' -ForegroundColor Cyan
    Write-Host 'Configurações locais, credenciais e logs serão preservados.' -ForegroundColor Gray
  }

  $tempRoot = Join-Path $env:TEMP ("Orquestra-update-" + [guid]::NewGuid().ToString('N'))
  $extractRoot = Join-Path $tempRoot 'extract'
  New-Item -ItemType Directory -Force -Path $extractRoot | Out-Null
  $zipPath = Join-Path $tempRoot 'orquestra-update.zip'
  $archiveUrl = "https://codeload.github.com/$($script:Owner)/$($script:Repository)/zip/$remoteCommit"
  Invoke-WebRequest -Uri $archiveUrl -OutFile $zipPath -TimeoutSec 90 -UseBasicParsing
  if (-not (Test-Path -LiteralPath $zipPath -PathType Leaf) -or (Get-Item -LiteralPath $zipPath).Length -lt 1024) {
    throw 'O pacote baixado está vazio ou incompleto.'
  }
  Expand-Archive -LiteralPath $zipPath -DestinationPath $extractRoot -Force
  $roots = @(Get-ChildItem -LiteralPath $extractRoot -Directory)
  if ($roots.Count -ne 1) { throw 'A estrutura do pacote do GitHub é inesperada.' }
  $sourceRoot = $roots[0].FullName
  foreach ($required in @('ABRIR-ORQUESTRA.cmd','launcher\OrquestraMenu.ps1','launcher\OrquestraUpdater.ps1')) {
    if (-not (Test-Path -LiteralPath (Join-Path $sourceRoot $required) -PathType Leaf)) {
      throw ("O pacote não passou na validação: falta " + $required)
    }
  }

  Copy-UpdateFiles -SourceRoot $sourceRoot -TargetRoot $script:InstallRoot

  $newState = [ordered]@{
    repository = "$($script:Owner)/$($script:Repository)"
    branch = $script:Branch
    commit = $remoteCommit
    install_root = $script:InstallRoot
    installed_at = (Get-Date).ToString('o')
  }
  [IO.File]::WriteAllText($stateFile, ($newState | ConvertTo-Json -Depth 4), [Text.UTF8Encoding]::new($false))
  Write-UpdateNotice ("Orquestra atualizada automaticamente para " + $remoteCommit.Substring(0,7) + ".")
  Write-UpdateLog ("UPDATE_OK | " + $remoteCommit)
  if (-not $Quiet) {
    Write-Host ("Atualização concluída: " + $remoteCommit.Substring(0,7)) -ForegroundColor Green
    Write-Host 'As configurações locais foram preservadas.' -ForegroundColor Gray
  }
  $exitCode = 10
} catch {
  Write-UpdateLog ("UPDATE_ERROR | " + $_.Exception.GetType().Name + " | " + $_.Exception.Message)
  if (-not $Quiet) {
    Write-Host ("Não foi possível atualizar. A instalação atual foi mantida. Detalhe: " + $_.Exception.Message) -ForegroundColor Yellow
  }
  $exitCode = 1
} finally {
  if ($tempRoot -and (Test-Path -LiteralPath $tempRoot)) {
    Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
  }
}
exit $exitCode
