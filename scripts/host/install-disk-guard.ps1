param(
    [ValidateSet('Plan', 'Install', 'Verify', 'Uninstall')]
    [string]$Mode = 'Install',
    [switch]$TestMode,
    [string]$TaskXmlPath,
    [string]$InstalledScriptPath,
    [string]$TaskState
)

$ErrorActionPreference = 'Stop'

$taskName = 'ForjaOS-Docker-Disk-Guard'
$source = Join-Path $PSScriptRoot 'check-disk.ps1'
$targetDir = Join-Path $env:LOCALAPPDATA 'ForjaOS\disk-guard'
$target = Join-Path $targetDir 'check-disk.ps1'

function Get-XmlValue([Xml.XmlNode]$node, [string]$xpath) {
    $selected = $node.SelectSingleNode($xpath)
    if ($null -eq $selected) { return '' }
    return [string]$selected.InnerText
}

if (-not (Test-Path -LiteralPath $source)) {
    Write-Error "Guard script not found: $source"
    exit 3
}

if ($TestMode) {
    if ($Mode -ne 'Verify' -or -not $TaskXmlPath -or -not $InstalledScriptPath -or -not $TaskState) {
        Write-Error 'TestMode requires Verify and fixture paths and state.'
        exit 3
    }
    $target = $InstalledScriptPath
    $targetDir = Split-Path -Parent $target
} elseif ($TaskXmlPath -or $InstalledScriptPath -or $TaskState) {
    Write-Error 'Fixture overrides require TestMode.'
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
    if ($TestMode) {
        $taskXml = [xml](Get-Content -LiteralPath $TaskXmlPath -Raw -ErrorAction Stop)
        $state = $TaskState
    } else {
        $task = Get-ScheduledTask -TaskName $taskName -ErrorAction Stop
        $taskXml = [xml](Export-ScheduledTask -TaskName $taskName -ErrorAction Stop)
        $state = [string]$task.State
    }
    if (-not (Test-Path -LiteralPath $target)) {
        Write-Error "Installed script not found: $target"
        exit 3
    }

    $errors = @()
    if ($state -notin @('Ready', 'Running')) { $errors += 'state' }
    $hasher = [Security.Cryptography.SHA256]::Create()
    try {
        $targetHash = [Convert]::ToBase64String($hasher.ComputeHash([IO.File]::ReadAllBytes($target)))
        $sourceHash = [Convert]::ToBase64String($hasher.ComputeHash([IO.File]::ReadAllBytes($source)))
    } finally {
        $hasher.Dispose()
    }
    if ($targetHash -ne $sourceHash) { $errors += 'script_hash' }

    $triggers = $taskXml.SelectNodes("/*[local-name()='Task']/*[local-name()='Triggers']/*")
    if ($triggers.Count -ne 1 -or $triggers[0].LocalName -ne 'CalendarTrigger') {
        $errors += 'trigger_count_or_type'
    } else {
        $trigger = $triggers[0]
        if ((Get-XmlValue $trigger "*[local-name()='Repetition']/*[local-name()='Interval']") -ne 'PT1M' -or
            (Get-XmlValue $trigger "*[local-name()='Repetition']/*[local-name()='Duration']") -ne 'P1D' -or
            (Get-XmlValue $trigger "*[local-name()='ScheduleByDay']/*[local-name()='DaysInterval']") -ne '1' -or
            (Get-XmlValue $trigger "*[local-name()='Enabled']") -eq 'false') {
            $errors += 'trigger_schedule'
        }
    }

    $principals = $taskXml.SelectNodes("/*[local-name()='Task']/*[local-name()='Principals']/*")
    $expectedSid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    if ($principals.Count -ne 1 -or
        (Get-XmlValue $principals[0] "*[local-name()='UserId']") -ne $expectedSid -or
        (Get-XmlValue $principals[0] "*[local-name()='LogonType']") -ne 'InteractiveToken' -or
        (Get-XmlValue $principals[0] "*[local-name()='RunLevel']") -notin @('', 'LeastPrivilege')) {
        $errors += 'principal'
    }

    $settings = $taskXml.SelectSingleNode("/*[local-name()='Task']/*[local-name()='Settings']")
    if ($null -eq $settings -or
        (Get-XmlValue $settings "*[local-name()='Enabled']") -eq 'false' -or
        (Get-XmlValue $settings "*[local-name()='StartWhenAvailable']") -ne 'true' -or
        (Get-XmlValue $settings "*[local-name()='DisallowStartIfOnBatteries']") -ne 'false' -or
        (Get-XmlValue $settings "*[local-name()='StopIfGoingOnBatteries']") -ne 'false' -or
        (Get-XmlValue $settings "*[local-name()='ExecutionTimeLimit']") -ne 'PT3M' -or
        (Get-XmlValue $settings "*[local-name()='MultipleInstancesPolicy']") -ne 'IgnoreNew') {
        $errors += 'settings'
    }

    $actions = $taskXml.SelectNodes("/*[local-name()='Task']/*[local-name()='Actions']/*")
    $expectedCommand = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
    $expectedArguments = '-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "' + $target + '" -Mode Watch'
    if ($actions.Count -ne 1 -or $actions[0].LocalName -ne 'Exec' -or
        (Get-XmlValue $actions[0] "*[local-name()='Command']") -ine $expectedCommand -or
        (Get-XmlValue $actions[0] "*[local-name()='Arguments']") -cne $expectedArguments -or
        (Get-XmlValue $actions[0] "*[local-name()='WorkingDirectory']") -ine $targetDir) {
        $errors += 'action'
    }

    if ($errors.Count) {
        Write-Error "Scheduled guard contract invalid: $($errors -join ', ')"
        exit 3
    }
    Write-Output "RESULT=VERIFIED TASK=$taskName STATE=$state TARGET=$target INTERVAL_MIN=1"
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
