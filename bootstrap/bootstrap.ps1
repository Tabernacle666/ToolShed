# One-time setup of D:\gitlink. Safe to run again.
$IsAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $IsAdmin) {
    Start-Process powershell -Verb RunAs -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`""
    exit
}
$ErrorActionPreference = "Stop"
try {
    $Kit  = Split-Path -Parent $PSScriptRoot
    $Cfg  = Get-Content (Join-Path $Kit "tools\config.json") -Raw | ConvertFrom-Json
    $Root = $Cfg.root
    New-Item -ItemType Directory -Force -Path "$Root\logs" | Out-Null
    $Log = "$Root\logs\bootstrap.log"
    function Step($m) { Write-Host "`n=== $m ===" -ForegroundColor Cyan; Add-Content $Log "$(Get-Date -Format s) $m" }

    Step "1/6 Folders"
    foreach ($d in "Apps","Engines","RawAssets","temp","cache\DDC","cache\UnrealEngine","cache\nuget","cache\pip","cache\VSCache","cache\Vault") {
        New-Item -ItemType Directory -Force -Path "$Root\\$d" | Out-Null
    }

    Step "2/6 Redirect caches and temp to $Root"
    $vars = [ordered]@{
        "UE-LocalDataCachePath" = "$Root\cache\DDC"
        "TEMP" = "$Root\temp"; "TMP" = "$Root\temp"
        "NUGET_PACKAGES" = "$Root\cache\nuget"; "PIP_CACHE_DIR" = "$Root\cache\pip"
    }
    foreach ($k in $vars.Keys) {
        [Environment]::SetEnvironmentVariable($k, $vars[$k], "User")
        [Environment]::SetEnvironmentVariable($k, $vars[$k], "Process")
    }
    $ueLocal = Join-Path $env:LOCALAPPDATA "UnrealEngine"
    if (-not (Test-Path $ueLocal)) {
        New-Item -ItemType Junction -Path $ueLocal -Target "$Root\cache\UnrealEngine" | Out-Null
    } elseif (-not ((Get-Item $ueLocal -Force).Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        Write-Warning "$ueLocal is a normal folder. Move its contents to $Root\cache\UnrealEngine, delete it, run again."
    }

    Step "3/6 Software (installers may take a while)"
    function Install($id, [string[]]$extra) {
        Write-Host "Installing $id"
        & winget install --id $id -e --accept-package-agreements --accept-source-agreements @extra
        if ($LASTEXITCODE -ne 0) { Write-Warning "$id exit code $LASTEXITCODE (often means already installed)" }
    }
    Install "Git.Git" @("--location", "$Root\Apps\Git")
    Install "Python.Python.3.12" @("--override", "/quiet InstallAllUsers=0 PrependPath=0 Include_launcher=0 TargetDir=$Root\Apps\Python312")
    Install "EpicGames.EpicGamesLauncher" @("--location", "$Root\Apps\EpicGamesLauncher")
    Install "Microsoft.VisualStudio.2022.BuildTools" @("--override", "--quiet --wait --norestart --installPath $Root\Apps\VSBuildTools --path cache=$Root\cache\VSCache --path shared=$Root\Apps\VSShared --add Microsoft.VisualStudio.Workload.VCTools --add Microsoft.VisualStudio.Component.Windows11SDK.22621 --includeRecommended")

    Step "4/6 Locate Git and Python"
    $env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [Environment]::GetEnvironmentVariable("Path","User")
    $git = @("$Root\Apps\Git\cmd\git.exe", "C:\Program Files\Git\cmd\git.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $git) { throw "git.exe not found. Run this script again once the Git installer has finished." }
    $pyw = $Cfg.python
    if (-not (Test-Path $pyw)) { throw "Python not found at $pyw. Run this script again." }
    & (Join-Path (Split-Path $pyw) "python.exe") -m pip install --upgrade pillow

    Step "5/6 Clone the repo (a GitHub sign-in window may open)"
    $repo = $Cfg.repo_dir
    if (-not (Test-Path "$repo\\.git")) {
        & $git clone $Cfg.repo_url $repo
        if ($LASTEXITCODE) { throw "git clone failed" }
    }
    & $git config --global --add safe.directory ($repo -replace '\\','/')
    & $git -C $repo config user.name  $Cfg.git_name
    & $git -C $repo config user.email $Cfg.git_email
    & $git -C $repo lfs install --local
    @{ git_exe = $git } | ConvertTo-Json | Set-Content "$repo\tools\local.json" -Encoding UTF8

    Step "6/6 Daemon autostart at sign-in"
    $me        = "$env:USERDOMAIN\\$env:USERNAME"
    $action    = New-ScheduledTaskAction -Execute $pyw -Argument "`"$repo\tools\ue_daemon.py`"" -WorkingDirectory $repo
    $trigger   = New-ScheduledTaskTrigger -AtLogOn -User $me
    $principal = New-ScheduledTaskPrincipal -UserId $me -LogonType Interactive -RunLevel Limited
    $settings  = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
    Register-ScheduledTask -TaskName "GitlinkDaemon" -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null

    Write-Host "`nDONE. Now SIGN OUT of Windows and sign back in. Then follow bootstrap\MANUAL_STEPS.md." -ForegroundColor Green
}
catch {
    Write-Host "`nERROR: $_" -ForegroundColor Red
    Add-Content $Log "$(Get-Date -Format s) ERROR $_"
}
finally { Read-Host "Press Enter to close" }
