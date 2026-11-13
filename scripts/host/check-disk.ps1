param(
    [ValidateSet('Check', 'Watch')]
    [string]$Mode = 'Check',
    [double]$FreeGiBOverride = -1,
    [switch]$DryRun,
    [switch]$TestMode,
    [string]$DockerCliOverride
)

$minStartGiB = 160
$stopGiB = 120
$dockerData = Join-Path $env:LOCALAPPDATA 'Docker\wsl\disk\docker_data.vhdx'
$dockerCli = Join-Path $env:LOCALAPPDATA 'Programs\DockerDesktop\resources\bin\docker.exe'
$guardDir = Join-Path $env:LOCALAPPDATA 'ForjaOS\disk-guard'
$log = Join-Path $guardDir 'events.log'

function Write-GuardEvent([string]$message) {
    New-Item -ItemType Directory -Path $guardDir -Force | Out-Null
    if ((Test-Path -LiteralPath $log) -and (Get-Item -LiteralPath $log).Length -gt 1MB) {
        Move-Item -LiteralPath $log -Destination (Join-Path $guardDir 'events.previous.log') -Force
    }
    Add-Content -LiteralPath $log -Value ('{0:o} {1}' -f (Get-Date), $message)
}

if ($TestMode) {
    if ($DryRun -or $FreeGiBOverride -lt 0 -or -not $DockerCliOverride -or
        -not (Test-Path -LiteralPath $DockerCliOverride) -or
        ([IO.Path]::GetFullPath($DockerCliOverride) -eq [IO.Path]::GetFullPath($dockerCli))) {
        Write-Error 'TestMode requires a free-space override and a non-Docker stub CLI.'
        exit 3
    }
    $dockerCli = $DockerCliOverride
    $guardDir = Join-Path (Split-Path -Parent $DockerCliOverride) 'guard-output'
    $log = Join-Path $guardDir 'events.log'
} elseif ($DockerCliOverride -or ($FreeGiBOverride -ge 0 -and -not $DryRun)) {
    Write-Error 'Overrides require DryRun or TestMode with a stub CLI.'
    exit 3
}

try {
    if ($FreeGiBOverride -ge 0) {
        $freeGiB = $FreeGiBOverride
    } else {
        $freeGiB = [IO.DriveInfo]::new('C:\').AvailableFreeSpace / 1GB
    }
} catch {
    Write-Error "Cannot read C: free space: $_"
    exit 3
}

$freeText = $freeGiB.ToString('F2', [Globalization.CultureInfo]::InvariantCulture)

if ($Mode -eq 'Check') {
    if (-not $DryRun -and -not (Test-Path -LiteralPath $dockerData)) {
        Write-Output "C_FREE_GIB=$freeText RESULT=BLOCK_DOCKER_DATA_LOCATION"
        exit 3
    }
    if ($freeGiB -lt $minStartGiB) {
        Write-Output "C_FREE_GIB=$freeText MIN_START_GIB=$minStartGiB RESULT=BLOCK"
        exit 2
    }
    Write-Output "C_FREE_GIB=$freeText MIN_START_GIB=$minStartGiB RESULT=PASS"
    exit 0
}

if ($freeGiB -ge $stopGiB) {
    Write-Output "C_FREE_GIB=$freeText STOP_GIB=$stopGiB RESULT=SAFE"
    exit 0
}

if ($DryRun) {
    Write-Output "C_FREE_GIB=$freeText STOP_GIB=$stopGiB RESULT=WOULD_STOP_DOCKER"
    exit 0
}

if (-not $TestMode -and -not (Get-Process -Name 'com.docker.backend' -ErrorAction SilentlyContinue)) {
    Write-Output "C_FREE_GIB=$freeText STOP_GIB=$stopGiB RESULT=DOCKER_ALREADY_STOPPED"
    exit 0
}

if (-not (Test-Path -LiteralPath $dockerCli)) {
    Write-GuardEvent "STOP_FAILED free_gib=$freeText reason=docker_cli_missing"
    Write-Error 'Docker Desktop CLI not found; cannot stop Docker.'
    exit 3
}

& $dockerCli desktop stop --timeout 120 *> $null
if ($LASTEXITCODE -ne 0) {
    Write-GuardEvent "STOP_FAILED free_gib=$freeText exit_code=$LASTEXITCODE"
    Write-Error "Docker Desktop stop failed with exit code $LASTEXITCODE."
    exit 3
}

Write-GuardEvent "DOCKER_STOPPED free_gib=$freeText"
Write-Output "C_FREE_GIB=$freeText STOP_GIB=$stopGiB RESULT=STOPPED_DOCKER"
exit 0
