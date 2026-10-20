$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSHOME 'Modules\Microsoft.PowerShell.Utility\Microsoft.PowerShell.Utility.psd1') -Force
$target=Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$state=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'state.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$allowed=@('SteelEmpire.exe','SteelRework.exe','SteelRework169.exe','SteelReworkQHD.exe','SteelCharacterEditor.exe','patch104.pak','ReworkCharacterTemplates.dat','ddraw.dll','ddraw.ini','SteelCharacterEditor-사용법.txt','SteelRework169-사용법.txt')
foreach($p in Get-Process -Name SteelEmpire,SteelRework,SteelRework169,SteelReworkQHD,SteelCharacterEditor -ErrorAction SilentlyContinue){
 if($p.Path -and (Split-Path -Parent $p.Path) -eq $target){throw 'Close the game, launchers and editor first.'}
}
foreach($entry in $state){
 if($entry.name -notin $allowed){throw 'Unexpected backup name.'}
 if($entry.existed -and (Get-FileHash -LiteralPath (Join-Path $PSScriptRoot $entry.name)).Hash.ToLowerInvariant() -ne $entry.original_sha256){throw 'Backup hash mismatch.'}
 $path=Join-Path $target $entry.name
 if((Test-Path -LiteralPath $path) -and (Get-FileHash -LiteralPath $path).Hash.ToLowerInvariant() -ne $entry.installed_sha256){throw "File changed after update: $path"}
}
foreach($entry in $state){
 $path=Join-Path $target $entry.name
 if($entry.existed){Copy-Item -LiteralPath (Join-Path $PSScriptRoot $entry.name) -Destination $path -Force}
 elseif(Test-Path -LiteralPath $path){Remove-Item -LiteralPath $path}
}
Write-Output 'Program files restored. Save files were not modified.'
