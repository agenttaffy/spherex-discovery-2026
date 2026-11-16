$demoRoot = Split-Path -Parent $PSScriptRoot
$demoRunDirectory = Join-Path $demoRoot '.spherex-demo.local'
$demoStatePath = Join-Path $demoRunDirectory 'processes.json'

function Lock-DemoRun {
    [void][IO.Directory]::CreateDirectory($demoRunDirectory)
    try {
        [IO.File]::Open((Join-Path $demoRunDirectory 'launcher.lock'), 'OpenOrCreate', 'ReadWrite', 'None')
    } catch {
        throw 'Another demo launch or stop is in progress.'
    }
}

function Get-DemoManifest($Root, $Dataset) {
    $cache = Join-Path $Root 'data/cache'
    $fitsDirectory = if ($Dataset -eq 'Original') { $cache } else { Join-Path $cache 'demo_multiepoch' }
    $relativePath = if ($Dataset -eq 'Original') { 'data/manifests/demo_dataset.json' } else { 'data/cache/demo_multiepoch/demo_dataset.json' }
    $manifestPath = Join-Path $Root $relativePath
    $expectedCount = if ($Dataset -eq 'Original') { 22 } else { 10 }
    if (!(Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
        throw "Missing $Dataset demo manifest at $manifestPath."
    }
    $rows = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($rows.Count -ne $expectedCount) {
        throw "$Dataset manifest has $($rows.Count) entries. Expected $expectedCount."
    }
    $hasher = [Security.Cryptography.SHA256]::Create()
    try {
        foreach ($row in $rows) {
            if ([string]::IsNullOrWhiteSpace($row.cutout_url)) { throw 'A demo manifest row lacks a cutout URL.' }
            $digest = $hasher.ComputeHash([Text.Encoding]::UTF8.GetBytes($row.cutout_url))
            $name = [BitConverter]::ToString($digest).Replace('-', '').ToLowerInvariant() + '.fits'
            $file = Get-Item -LiteralPath (Join-Path $fitsDirectory $name) -ErrorAction SilentlyContinue
            if (!$file -or $file.PSIsContainer -or $file.Length -eq 0) {
                throw "Missing or empty cache file for $($row.target_name) ($($row.obs_id)): $(Join-Path $fitsDirectory $name)"
            }
        }
    } finally {
        $hasher.Dispose()
    }
    [pscustomobject]@{ Path = $manifestPath; FitsDirectory = $fitsDirectory; Rows = $rows }
}

function Assert-DemoPort($Port) {
    $listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, $Port)
    $listener.ExclusiveAddressUse = $true
    try {
        $listener.Start()
    } catch {
        throw "Port $Port on 127.0.0.1 is unavailable. Choose a different port or close its owner yourself."
    } finally {
        $listener.Stop()
    }
}

function Get-DemoProcessRecord($Role, $Process) {
    [pscustomobject]@{
        Role = $Role
        ProcessId = $Process.Id
        StartedUtcTicks = $Process.StartTime.ToUniversalTime().Ticks.ToString()
    }
}

function Stop-DemoProcesses($Records) {
    foreach ($record in $Records) {
        $process = Get-Process -Id $record.ProcessId -ErrorAction SilentlyContinue
        if (!$process) { continue }
        try {
            # Keep a handle to the original process while checking for PID reuse.
            $null = $process.Handle
            if ($process.StartTime.ToUniversalTime().Ticks.ToString() -ne $record.StartedUtcTicks) { continue }
            $process.Kill()
            if (!$process.WaitForExit(5000)) { throw "$($record.Role) process did not exit." }
        } catch {
            if (!$process.HasExited) { throw }
        } finally {
            $process.Dispose()
        }
    }
}

function Wait-DemoResponse($Url, $Processes, $Deadline, $Step) {
    while ([DateTime]::UtcNow -lt $Deadline) {
        foreach ($process in $Processes) {
            if ($process.HasExited) { throw "$Step failed. Process $($process.Id) exited with code $($process.ExitCode)." }
        }
        try {
            return Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 1 -ErrorAction Stop
        } catch {
            Start-Sleep -Milliseconds 200
        }
    }
    throw "$Step timed out at $Url."
}

function Assert-DemoManifestResponse($Response, $Rows) {
    $actual = $Response.Content | ConvertFrom-Json
    if ($actual.total_cached_cutouts -ne $Rows.Count -or $actual.presets_count -ne 5 -or
        @($actual.manifest).Count -ne $Rows.Count) {
        throw 'The API did not select the requested demo manifest.'
    }
    for ($index = 0; $index -lt $Rows.Count; $index++) {
        if ($actual.manifest[$index].cutout_url -cne $Rows[$index].cutout_url) {
            throw "The API selected a different cutout at manifest row $($index + 1)."
        }
    }
}
