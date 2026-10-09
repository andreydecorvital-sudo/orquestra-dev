# Prepare Hermes locally without remote scripts, API billing or cloud secrets.
# Does not execute a model or start the Orquestra worker.
$ErrorActionPreference='Stop'
if(-not (Get-Command hermes -ErrorAction SilentlyContinue)){
 throw 'Hermes não instalado. Instale apenas pela documentação oficial e abra novo PowerShell.'
}
$homeDir=if($env:HERMES_HOME){$env:HERMES_HOME}else{Join-Path $env:LOCALAPPDATA 'hermes'}
if(-not(Test-Path -LiteralPath $homeDir)){New-Item -ItemType Directory -Path $homeDir -Force | Out-Null}
$envFile=Join-Path $homeDir '.env'
$vals=@{}
if(Test-Path -LiteralPath $envFile){
 foreach($line in [System.IO.File]::ReadAllLines($envFile)){
   if($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)=(.*)$'){$vals[$matches[1]]=$matches[2]}
 }
}
if(-not $vals.ContainsKey('API_SERVER_KEY') -or $vals['API_SERVER_KEY'].Trim().Length -lt 32){
 $rng=[byte[]]::new(32)
 [Security.Cryptography.RandomNumberGenerator]::Fill($rng)
 $vals['API_SERVER_KEY']=[Convert]::ToHexString($rng).ToLowerInvariant()
}
$vals['API_SERVER_ENABLED']='true'
$vals['API_SERVER_HOST']='127.0.0.1'
$vals['API_SERVER_PORT']='8642'
$vals['API_SERVER_CORS_ORIGINS']=''
# Preserve unrelated existing Hermes variables and back up safely.
$contents=($vals.Keys|Sort-Object|ForEach-Object {"$_=$($vals[$_])"})-join [Environment]::NewLine
$temp=Join-Path $homeDir ('.env.orq-'+[Guid]::NewGuid().ToString('N')+'.tmp')
[IO.File]::WriteAllText($temp,$contents+[Environment]::NewLine,[Text.UTF8Encoding]::new($false))
$sid=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$ruleUser='*'+$sid+':(F)'
& icacls.exe $temp '/inheritance:r' '/grant:r' $ruleUser 'SYSTEM:(F)' 1>$null 2>$null
if($LASTEXITCODE -ne 0){Remove-Item $temp -Force;throw 'Falha ao proteger segredo Hermes'}
if(Test-Path -LiteralPath $envFile){
 $backup=Join-Path $homeDir ('.env.backup-'+[Guid]::NewGuid().ToString('N'))
 Copy-Item -LiteralPath $envFile -Destination $backup
 & icacls.exe $backup '/inheritance:r' '/grant:r' $ruleUser 'SYSTEM:(F)' 1>$null 2>$null
 if($LASTEXITCODE -ne 0){Remove-Item $backup -Force;Remove-Item $temp -Force;throw 'Falha ao proteger backup'}
}
Move-Item -LiteralPath $temp -Destination $envFile -Force
Write-Host 'API Hermes configurada em localhost:8642. Chave privada salva localmente.' -ForegroundColor Green
Write-Host 'Agora desative todas as ferramentas do perfil API em: hermes tools'
Write-Host 'Após configurar um modelo permitido: hermes gateway'
Write-Host 'A Orquestra só anuncia Hermes quando o perfil API estiver sem ferramentas ativas.'
