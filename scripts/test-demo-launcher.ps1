$ErrorActionPreference = 'Stop'
. "$PSScriptRoot/demo-launcher-common.ps1"

function Assert-Throws($Action, $Pattern) {
    try { & $Action } catch {
        if ($_.Exception.Message -match $Pattern) { return }
        throw
    }
    throw "Expected an error matching '$Pattern'."
}

Assert-Throws { & "$PSScriptRoot/start-demo.ps1" -Dataset Other } 'ValidateSet|does not belong'
Assert-Throws { & "$PSScriptRoot/start-demo.ps1" -ApiPort 0 } 'range|greater than'
Assert-Throws { & "$PSScriptRoot/start-demo.ps1" -ApiPort 5513 -AppPort 5513 } 'different ports'
Write-Host 'PASS argument validation'

$preview = Get-DemoManifest $demoRoot Preview
$originalPath = Join-Path $demoRoot 'data/manifests/demo_dataset.json'
$originalRows = Get-Content -LiteralPath $originalPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ($preview.Rows.Count -ne 10 -or $originalRows.Count -ne 22) { throw 'Wrong manifest selection.' }
$manifestJson = Get-Content -LiteralPath $preview.Path -Raw -Encoding UTF8
$match = [pscustomobject]@{ Content = '{"total_cached_cutouts":10,"presets_count":5,"manifest":' + $manifestJson + '}' }
Assert-DemoManifestResponse $match $preview.Rows
Assert-Throws { Assert-DemoManifestResponse $match $originalRows } 'did not select'
$wrong = [pscustomobject]@{ Content = @{ total_cached_cutouts = 10; presets_count = 5; manifest = @(1..10 | ForEach-Object { @{ cutout_url = 'wrong' } }) } | ConvertTo-Json -Depth 5 }
Assert-Throws { Assert-DemoManifestResponse $wrong $preview.Rows } 'different cutout'
Write-Host 'PASS preview cache, original manifest metadata, and exact response verification'

$scratch = Join-Path ([IO.Path]::GetTempPath()) ('spherex-launcher-test-' + [guid]::NewGuid())
$emptyCache = Join-Path $scratch 'data/cache/demo_multiepoch'
[void][IO.Directory]::CreateDirectory($emptyCache)
$copiedManifest = Join-Path $emptyCache 'demo_dataset.json'
try {
    Copy-Item -LiteralPath $preview.Path -Destination $copiedManifest
    Assert-Throws { Get-DemoManifest $scratch Preview } 'Missing or empty cache file'
} finally {
    Remove-Item -LiteralPath $copiedManifest
    foreach ($directory in @($emptyCache, (Join-Path $scratch 'data/cache'), (Join-Path $scratch 'data'), $scratch)) {
        [IO.Directory]::Delete($directory)
    }
}
Write-Host 'PASS missing cache diagnosed before startup'

$listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, 0)
$listener.ExclusiveAddressUse = $true
$listener.Start()
try {
    $port = $listener.LocalEndpoint.Port
    Assert-Throws { Assert-DemoPort $port } 'unavailable'
    if (!$listener.Server.IsBound) { throw 'The unrelated listener was stopped.' }
} finally {
    $listener.Stop()
}
Write-Host 'PASS occupied port leaves the existing listener alone'

Assert-Throws { Wait-DemoResponse 'http://127.0.0.1:1/' @() ([DateTime]::UtcNow) 'Test startup' } 'Test startup timed out'
Write-Host 'PASS readiness timeout'

$node = (Get-Command node.exe -CommandType Application | Select-Object -First 1).Source
$owned = Start-Process -FilePath $node -ArgumentList @('-e', '"setInterval(()=>{},1000)"') -WindowStyle Hidden -PassThru
$unrelated = Start-Process -FilePath $node -ArgumentList @('-e', '"setInterval(()=>{},1000)"') -WindowStyle Hidden -PassThru
try {
    $record = Get-DemoProcessRecord 'Test child' $owned
    $wrongIdentity = Get-DemoProcessRecord 'Stale record' $unrelated
    $wrongIdentity.StartedUtcTicks = '1'
    Stop-DemoProcesses @($record, $wrongIdentity)
    if (!$owned.HasExited -or $unrelated.HasExited) { throw 'Unexpected process cleanup.' }
    Stop-DemoProcesses @($record)
} finally {
    foreach ($process in @($owned, $unrelated)) {
        if (!$process.HasExited) { $process.Kill() }
        $process.Dispose()
    }
}
Write-Host 'PASS cleanup stops owned processes and skips reused or stale process IDs'
