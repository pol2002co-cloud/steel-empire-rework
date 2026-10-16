param([Parameter(Mandatory=$true)][string]$GamePath)
$ErrorActionPreference='Stop'
$target=(Resolve-Path -LiteralPath $GamePath).Path.TrimEnd('\')
$manifest=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'release-manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$payload=Join-Path $PSScriptRoot 'payload'
foreach($p in Get-Process -Name SteelEmpire,SteelRework,SteelRework169,SteelReworkQHD,SteelCharacterEditor -ErrorAction SilentlyContinue){
 if($p.Path -and (Split-Path -Parent $p.Path) -eq $target){throw 'Close the game, launchers and editor first.'}
}
$exe=Join-Path $target 'SteelEmpire.exe'
if(!(Test-Path -LiteralPath $exe)){throw 'SteelEmpire.exe is missing.'}
$installedHash=(Get-FileHash -LiteralPath $exe).Hash.ToLowerInvariant()
if($installedHash -notin $manifest.supported_executable_hashes){throw 'Unsupported executable. No files changed.'}
if(!(Test-Path -LiteralPath (Join-Path $target 'Data.pak'))){throw 'Game data is missing.'}
$allowed=@('SteelEmpire.exe','SteelRework.exe','SteelRework169.exe','SteelReworkQHD.exe','SteelCharacterEditor.exe','patch104.pak','ddraw.dll','ddraw.ini','SteelCharacterEditor-사용법.txt','SteelRework169-사용법.txt')
$entries=@($manifest.payload.PSObject.Properties)
foreach($entry in $entries){
 if($entry.Name -notin $allowed){throw 'Unexpected payload name.'}
 if((Get-FileHash -LiteralPath (Join-Path $payload $entry.Name)).Hash.ToLowerInvariant() -ne $entry.Value){throw 'Payload hash mismatch.'}
}
$backup=Join-Path $target ('ReworkBackups\v'+$manifest.version+'-public-'+(Get-Date -Format yyyyMMdd-HHmmssfff))
New-Item -ItemType Directory -Path $backup | Out-Null
$state=@()
foreach($entry in $entries){
 $path=Join-Path $target $entry.Name
 if($entry.Name -eq 'ddraw.ini' -and (Test-Path -LiteralPath $path)){continue}
 $exists=Test-Path -LiteralPath $path
 $oldHash=$null
 if($exists){Copy-Item -LiteralPath $path -Destination (Join-Path $backup $entry.Name);$oldHash=(Get-FileHash -LiteralPath $path).Hash.ToLowerInvariant()}
 $state+=@{name=$entry.Name;existed=$exists;original_sha256=$oldHash;installed_sha256=$entry.Value}
}
ConvertTo-Json -InputObject @($state) | Set-Content -LiteralPath (Join-Path $backup 'state.json') -Encoding UTF8
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'Restore-Update.ps1') -Destination (Join-Path $backup 'Restore-Update.ps1')
try {
 foreach($entry in $state){
  $path=Join-Path $target $entry.name
  Copy-Item -LiteralPath (Join-Path $payload $entry.name) -Destination $path -Force
  if((Get-FileHash -LiteralPath $path).Hash.ToLowerInvariant() -ne $entry.installed_sha256){throw 'Installed hash mismatch.'}
 }
} catch {
 foreach($entry in $state){
  $path=Join-Path $target $entry.name
  if($entry.existed){Copy-Item -LiteralPath (Join-Path $backup $entry.name) -Destination $path -Force}
  elseif(Test-Path -LiteralPath $path){Remove-Item -LiteralPath $path}
 }
 throw
}
Write-Output "Installed v$($manifest.version). Backup: $backup"
Write-Output 'Save files were not modified. Personal quest repairs are not part of this update.'
