param(
    [ValidateSet('Plan', 'Install', 'Verify', 'Uninstall')]
    [string]$Mode = 'Install'
)

$taskName = 'ForjaOS-Docker-Disk-Guard'
$source = Join-Path $PSScriptRoot 'check-disk.ps1'
$targetDir = Join-Path $env:LOCALAPPDATA 'ForjaOS\disk-guard'
$target = Join-Path $targetDir 'check-disk.ps1'

if (-not (Test-Path -LiteralPath $source)) {
    Write-Error "Guard script not found: $source"
    exit 3
}

if ($Mode -eq 'Plan') {
    Write-Output "RESULT=PLAN TASK=$taskName TARGET=$target INTERVAL_MIN=1 LOGON=INTERACTIVE"
    exit 0
}

if ($Mode -eq 'Uninstall') {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction Stop
    Remove-Item -LiteralPath $target -Force -ErrorAction Stop
    Write-Output "RESULT=UNINSTALLED TASK=$taskName"
    exit 0
}

if ($Mode -eq 'Verify') {
    $task = Get-ScheduledTask -TaskName $taskName -ErrorAction Stop
    if (-not (Test-Path -LiteralPath $target)) {
        Write-Error "Installed script not found: $target"
        exit 3
    }
    if ($task.Actions[0].Arguments -notlike "*$target*" -or
        $task.Triggers[0].Repetition.Interval -ne 'PT1M') {
        Write-Error 'Scheduled task does not match the one-minute guard.'
        exit 3
    }
    Write-Output "RESULT=VERIFIED TASK=$taskName STATE=$($task.State) TARGET=$target INTERVAL_MIN=1"
    exit 0
}

New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
Copy-Item -LiteralPath $source -Destination $target -Force

$service = New-Object -ComObject 'Schedule.Service'
$service.Connect()
$definition = $service.NewTask(0)
$definition.RegistrationInfo.Description = 'Protect the Windows system SSD by stopping Docker Desktop below 120 GiB free.'
$definition.Principal.UserId = [Security.Principal.WindowsIdentity]::GetCurrent().Name
$definition.Principal.LogonType = 3  # TASK_LOGON_INTERACTIVE_TOKEN
$definition.Principal.RunLevel = 0   # TASK_RUNLEVEL_LUA
$definition.Settings.Enabled = $true
$definition.Settings.StartWhenAvailable = $true
$definition.Settings.DisallowStartIfOnBatteries = $false
$definition.Settings.StopIfGoingOnBatteries = $false
$definition.Settings.MultipleInstances = 2  # TASK_INSTANCES_IGNORE_NEW
$definition.Settings.ExecutionTimeLimit = 'PT3M'

$trigger = $definition.Triggers.Create(2)  # TASK_TRIGGER_DAILY
$trigger.StartBoundary = (Get-Date).AddMinutes(1).ToString('s')
$trigger.DaysInterval = 1
$trigger.Repetition.Interval = 'PT1M'
$trigger.Repetition.Duration = 'P1D'
$trigger.Enabled = $true

$action = $definition.Actions.Create(0)  # TASK_ACTION_EXEC
$action.Path = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$action.Arguments = '-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "' + $target + '" -Mode Watch'
$action.WorkingDirectory = $targetDir

$folder = $service.GetFolder('\')
$folder.RegisterTaskDefinition($taskName, $definition, 6, $null, $null, 3, $null) | Out-Null
Start-ScheduledTask -TaskName $taskName -ErrorAction Stop
Write-Output "RESULT=INSTALLED TASK=$taskName TARGET=$target INTERVAL_MIN=1"
