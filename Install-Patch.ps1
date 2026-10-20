param([string]$GamePath)
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSHOME 'Modules\Microsoft.PowerShell.Utility\Microsoft.PowerShell.Utility.psd1') -Force
if([string]::IsNullOrWhiteSpace($GamePath)){
 Add-Type -AssemblyName System.Windows.Forms
 $dialog=New-Object System.Windows.Forms.FolderBrowserDialog
 $dialog.Description='Select your original Steel Empire game folder.'
 $dialog.ShowNewFolderButton=$false
 try {if($dialog.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK){exit 0};$GamePath=$dialog.SelectedPath}finally{$dialog.Dispose()}
}
$target=(Resolve-Path -LiteralPath $GamePath).Path.TrimEnd('\')
$manifest=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'patch-manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
foreach($p in Get-Process -Name SteelEmpire,SteelRework,SteelRework169,SteelReworkQHD,SteelCharacterEditor -ErrorAction SilentlyContinue){
 if($p.Path -and (Split-Path -Parent $p.Path) -eq $target){throw 'Close the game, launchers and editor first.'}
}
$exe=Join-Path $target 'SteelEmpire.exe'
if(!(Test-Path -LiteralPath $exe)){throw 'SteelEmpire.exe is missing. Install your own original game first.'}
$installed=(Get-FileHash -LiteralPath $exe).Hash.ToLowerInvariant()
if($installed -notin $manifest.supported_executable_hashes){throw 'Unsupported installed executable. No files changed.'}
$candidates=@($exe)
$backups=Join-Path $target 'ReworkBackups'
if(Test-Path -LiteralPath $backups){$candidates+=@(Get-ChildItem -LiteralPath $backups -Filter SteelEmpire.exe -Recurse -File | ForEach-Object FullName)}
$original=$null
foreach($candidate in $candidates){if((Get-FileHash -LiteralPath $candidate).Hash.ToLowerInvariant() -eq $manifest.engine.source_sha256){$original=$candidate;break}}
if(!$original){throw 'Verified original SteelEmpire.exe is required in the game folder or ReworkBackups. No game files changed.'}
$allowed=@('SteelEmpire.exe','patch104.pak','ReworkCharacterTemplates.dat','SteelRework.exe','SteelRework169.exe','SteelReworkQHD.exe','SteelCharacterEditor.exe','ddraw.dll','ddraw.ini','SteelCharacterEditor-사용법.txt','SteelRework169-사용법.txt')
foreach($entry in $manifest.payload.PSObject.Properties){
 if($entry.Name -notin $allowed){throw 'Unexpected payload name.'}
 if((Get-FileHash -LiteralPath (Join-Path $PSScriptRoot ('payload\'+$entry.Name))).Hash.ToLowerInvariant() -ne $entry.Value){throw 'Payload verification failed.'}
}
$stage=Join-Path ([IO.Path]::GetTempPath()) ('SteelReworkPatch-'+[guid]::NewGuid().ToString('N'))
$backup=$null
try {
 Add-Type -Path (Join-Path $PSScriptRoot 'PatchEngine.cs') -ReferencedAssemblies System.Web.Extensions
 [PatchEngine]::Generate($target,$original,(Join-Path $PSScriptRoot 'patch-manifest.json'),$stage)
 foreach($entry in $manifest.payload.PSObject.Properties){Copy-Item -LiteralPath (Join-Path $PSScriptRoot ('payload\'+$entry.Name)) -Destination (Join-Path $stage $entry.Name)}
 $backup=Join-Path $target ('ReworkBackups\v'+$manifest.version+'-delta-'+(Get-Date -Format yyyyMMdd-HHmmssfff))
 New-Item -ItemType Directory -Path $backup | Out-Null
 $state=@()
 foreach($file in Get-ChildItem -LiteralPath $stage -File){
  if($file.Name -notin $allowed){throw 'Unexpected staged file.'}
  $path=Join-Path $target $file.Name
  if($file.Name -eq 'ddraw.ini' -and (Test-Path -LiteralPath $path)){continue}
  $exists=Test-Path -LiteralPath $path;$oldHash=$null
  if($exists){Copy-Item -LiteralPath $path -Destination (Join-Path $backup $file.Name);$oldHash=(Get-FileHash -LiteralPath $path).Hash.ToLowerInvariant()}
  $state+=@{name=$file.Name;existed=$exists;original_sha256=$oldHash;installed_sha256=(Get-FileHash -LiteralPath $file.FullName).Hash.ToLowerInvariant()}
 }
 ConvertTo-Json -InputObject @($state) | Set-Content -LiteralPath (Join-Path $backup 'state.json') -Encoding UTF8
 Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'Restore-Patch.ps1') -Destination (Join-Path $backup 'Restore-Patch.ps1')
 try {
  foreach($entry in $state){$path=Join-Path $target $entry.name;Copy-Item -LiteralPath (Join-Path $stage $entry.name) -Destination $path -Force
   if((Get-FileHash -LiteralPath $path).Hash.ToLowerInvariant() -ne $entry.installed_sha256){throw 'Installed file verification failed.'}}
 }catch{
  foreach($entry in $state){$path=Join-Path $target $entry.name;if($entry.existed){Copy-Item -LiteralPath (Join-Path $backup $entry.name) -Destination $path -Force}elseif(Test-Path -LiteralPath $path){Remove-Item -LiteralPath $path}}
  throw
 }
 Write-Output "Installed v$($manifest.version). Backup: $backup"
 Write-Output 'Existing saves and display settings were preserved.'
}finally{
 if(Test-Path -LiteralPath $stage){
  $resolved=[IO.Path]::GetFullPath($stage);$temp=[IO.Path]::GetFullPath([IO.Path]::GetTempPath())
  if(!$resolved.StartsWith($temp,[StringComparison]::OrdinalIgnoreCase) -or (Split-Path -Leaf $resolved) -notlike 'SteelReworkPatch-*'){throw 'Unexpected staging directory.'}
  Remove-Item -LiteralPath $resolved -Recurse -Force
 }
}
