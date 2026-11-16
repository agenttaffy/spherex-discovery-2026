[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot/demo-launcher-common.ps1"

$lock = Lock-DemoRun
try {
    if (!(Test-Path -LiteralPath $demoStatePath -PathType Leaf)) {
        Write-Host 'No launcher session is recorded.'
        return
    }
    $records = Get-Content -LiteralPath $demoStatePath -Raw -Encoding UTF8 | ConvertFrom-Json
    Stop-DemoProcesses $records
    Remove-Item -LiteralPath $demoStatePath
    Write-Host "SPHEREx demo stopped. Logs remain in $demoRunDirectory."
} finally {
    $lock.Dispose()
}
