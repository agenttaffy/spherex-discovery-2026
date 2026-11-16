[CmdletBinding()]
param(
    [ValidateSet('Preview', 'Original')][string]$Dataset = 'Preview',
    [ValidateRange(1, 65535)][int]$ApiPort = 8000,
    [ValidateRange(1, 65535)][int]$AppPort = 5173,
    [ValidateRange(1, 300)][int]$StartupTimeoutSeconds = 45,
    [switch]$Live,
    [switch]$NoBrowser
)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot/demo-launcher-common.ps1"

if ($ApiPort -eq $AppPort) { throw 'The app and API need different ports.' }
$lock = Lock-DemoRun
$processes = @()
$records = @()
$logDirectory = $null
try {
    if (Test-Path -LiteralPath $demoStatePath) {
        throw 'A previous launcher session is recorded. Run scripts/stop-demo.ps1 before starting again.'
    }
    Assert-DemoPort $ApiPort
    Assert-DemoPort $AppPort

    $python = Get-Command python.exe -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    $node = Get-Command node.exe -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    $npm = Get-Command npm.cmd -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if (!$python -or !$node -or !$npm) { throw 'Install Python 3.11+ and Node.js 18+ with npm and make them available on PATH.' }
    & $python.Source -c "import sys; sys.exit(sys.version_info < (3, 11))"
    if ($LASTEXITCODE) { throw 'Python 3.11 or later is required.' }
    & $node.Source -e "process.exit(Number(process.versions.node.split('.')[0]) < 18 ? 1 : 0)"
    if ($LASTEXITCODE) { throw 'Node.js 18 or later is required.' }

    $backend = Join-Path $demoRoot 'backend'
    $frontend = Join-Path $demoRoot 'frontend'
    Push-Location -LiteralPath $backend
    try {
        & $python.Source -c "import uvicorn, reproject, pyvo, astroquery; from app.main import app"
        if ($LASTEXITCODE) { throw 'Backend dependencies failed to load. Run python -m pip install -r backend/requirements.txt from the repository root.' }
    } finally { Pop-Location }
    Push-Location -LiteralPath $frontend
    try {
        & $npm.Source ls --depth=0 --silent | Out-Null
        if ($LASTEXITCODE -or !(Test-Path -LiteralPath 'node_modules/vite/bin/vite.js' -PathType Leaf)) {
            throw 'Frontend dependencies are missing or invalid. Run npm.cmd ci --prefix frontend from the repository root.'
        }
    } finally { Pop-Location }

    if ($Dataset -eq 'Preview') {
        & $python.Source (Join-Path $PSScriptRoot 'bootstrap_demo_data.py') --check-only
        if ($LASTEXITCODE) { throw 'Preview data verification failed. Run python scripts/bootstrap_demo_data.py from the repository root with Internet access.' }
    }
    $manifest = Get-DemoManifest $demoRoot $Dataset

    $logDirectory = Join-Path $demoRunDirectory (Get-Date -Format 'yyyyMMdd-HHmmss-fff')
    [void][IO.Directory]::CreateDirectory($logDirectory)
    $auditPath = Join-Path $logDirectory 'fits-audit.json'
    $auditArgs = @((Join-Path $PSScriptRoot 'audit_demo_manifest.py'), '--manifest', $manifest.Path, '--cache-dir', $manifest.FitsDirectory, '--json', '--output', $auditPath)
    if ($Dataset -eq 'Preview') { $auditArgs += '--strict' }
    & $python.Source @auditArgs
    if ($LASTEXITCODE) { throw "The $Dataset FITS audit failed. See $auditPath and restore the affected files." }

    $previousManifest = $env:SPHEREX_DEMO_MANIFEST
    $previousCacheMode = $env:SPHEREX_DEMO_CACHE_ONLY
    $previousApiPort = $env:SPHEREX_DEMO_API_PORT
    try {
        $env:SPHEREX_DEMO_MANIFEST = $manifest.Path
        $env:SPHEREX_DEMO_CACHE_ONLY = if ($Live) { '0' } else { '1' }
        $api = Start-Process -FilePath $python.Source -WorkingDirectory $backend -ArgumentList @('-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', $ApiPort) -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $logDirectory 'backend.log') -RedirectStandardError (Join-Path $logDirectory 'backend-error.log')
        $processes += $api
        $records += Get-DemoProcessRecord 'Backend' $api
        ConvertTo-Json -InputObject $records | Set-Content -LiteralPath $demoStatePath -Encoding UTF8
        $env:SPHEREX_DEMO_API_PORT = "$ApiPort"
        $web = Start-Process -FilePath $node.Source -WorkingDirectory $frontend -ArgumentList @('node_modules/vite/bin/vite.js', '--host', '127.0.0.1', '--port', $AppPort, '--strictPort') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $logDirectory 'frontend.log') -RedirectStandardError (Join-Path $logDirectory 'frontend-error.log')
        $processes += $web
        $records += Get-DemoProcessRecord 'Frontend' $web
        ConvertTo-Json -InputObject $records | Set-Content -LiteralPath $demoStatePath -Encoding UTF8
    } finally {
        $env:SPHEREX_DEMO_MANIFEST = $previousManifest
        $env:SPHEREX_DEMO_CACHE_ONLY = $previousCacheMode
        $env:SPHEREX_DEMO_API_PORT = $previousApiPort
    }

    $apiUrl = "http://127.0.0.1:$ApiPort"
    $appUrl = "http://127.0.0.1:$AppPort"
    $deadline = [DateTime]::UtcNow.AddSeconds($StartupTimeoutSeconds)
    $health = (Wait-DemoResponse "$apiUrl/api/ready" $processes $deadline 'Backend readiness check').Content | ConvertFrom-Json
    if ($health.status -ne 'healthy' -or ([bool]$health.demo_cache_only -eq [bool]$Live)) {
        throw 'The backend health response did not confirm the requested observation mode.'
    }
    Assert-DemoManifestResponse (Wait-DemoResponse "$apiUrl/api/demo/manifest" $processes $deadline 'Backend manifest check') $manifest.Rows
    $page = Wait-DemoResponse "$appUrl/" $processes $deadline 'Frontend page check'
    if ($page.Content -notmatch 'SPHEREx Discovery') { throw 'The frontend responded with an unexpected page.' }
    Assert-DemoManifestResponse (Wait-DemoResponse "$appUrl/api/demo/manifest" $processes $deadline 'Frontend API proxy check') $manifest.Rows

    Write-Host "App: $appUrl/"
    Write-Host "API: $apiUrl/api/health | Manifest: $apiUrl/api/demo/manifest"
    Write-Host "Selected manifest ($($manifest.Rows.Count) frames): $($manifest.Path)"
    if ($Live) { Write-Host 'Live archive search is enabled. Cached observations may be returned if the archive is unavailable.' }
    Write-Host "Logs: $logDirectory"
    if ($Dataset -eq 'Preview') {
        Write-Host 'The cached preview has two covered epochs per preset. Source identity, target flux, motion, and variability remain unconfirmed.'
        Write-Host 'WISE 0855 supports blink. Its tested calibrated difference and pair co-add return HTTP 422 for incompatible passbands.'
    } else {
        Write-Host 'Original data: 18 preset-field cutouts and four documentation examples. Only four RW Aurigae cutouts cover a preset prediction at exposure time.'
    }
    Write-Host 'Field aperture checks provide no source detection or target flux.'
    Write-Host 'Spectral Cube uses verified cached sky-pixel samples for preview coordinates and offers a latest-archive check.'
    if (!$NoBrowser) {
        try { Start-Process "$appUrl/" } catch { Write-Warning "Open $appUrl/ in your browser. The demo is running." }
    }
} catch {
    if ($logDirectory) { Write-Warning "Startup logs: $logDirectory" }
    foreach ($process in $processes) {
        if (!$process.HasExited) {
            try {
                $process.Kill()
                if (!$process.WaitForExit(5000)) { throw 'Process did not exit.' }
            } catch {
                Write-Warning "Could not stop process $($process.Id): $_"
            }
        }
    }
    $remaining = @($records | Where-Object { $_.ProcessId -in @($processes | Where-Object { !$_.HasExited } | ForEach-Object Id) })
    if ($remaining.Count) {
        ConvertTo-Json -InputObject $remaining | Set-Content -LiteralPath $demoStatePath -Encoding UTF8
    } elseif ($records.Count -and (Test-Path -LiteralPath $demoStatePath -PathType Leaf)) {
        Remove-Item -LiteralPath $demoStatePath
    }
    throw
} finally {
    $lock.Dispose()
}
