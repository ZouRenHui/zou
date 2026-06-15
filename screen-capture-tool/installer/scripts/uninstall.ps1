#Requires -Version 5.1
<#
.SYNOPSIS
  卸载「录屏截屏工具」— 结束进程、调用官方卸载器或清理残留文件与快捷方式。

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File uninstall.ps1

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File uninstall.ps1 -Silent
#>
param(
    [switch]$Silent
)

$ErrorActionPreference = "Stop"

$AppId = "{C3D8E2F1-4A6B-5C9D-0E1F-030000000003}"
$AppName = "录屏截屏工具"
$ExeName = "ScreenCapture.exe"
$DefaultFolder = "ScreenCapture"
$UninstallRegSuffix = "${AppId}_is1"

function Write-Step([string]$Message) {
    if (-not $Silent) {
        Write-Host $Message
    }
}

function Confirm-Uninstall {
    if ($Silent) {
        return $true
    }
    Write-Host "========================================"
    Write-Host " $AppName — 卸载"
    Write-Host "========================================"
    Write-Host ""
    $answer = Read-Host "确定要卸载旧版本吗？(Y/N)"
    return $answer -match "^[Yy]"
}

function Stop-AppProcess {
    $procs = Get-Process -Name "ScreenCapture" -ErrorAction SilentlyContinue
    if (-not $procs) {
        Write-Step "[OK] 未发现正在运行的程序"
        return
    }
    Write-Step "正在结束 $ExeName ..."
    Stop-Process -Name "ScreenCapture" -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
    Write-Step "[OK] 已结束运行中的程序"
}

function Get-UninstallRegistryEntry {
    $paths = @(
        "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\$UninstallRegSuffix",
        "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\$UninstallRegSuffix"
    )
    foreach ($path in $paths) {
        if (Test-Path $path) {
            return Get-ItemProperty -Path $path
        }
    }
    return $null
}

function Invoke-RegisteredUninstaller {
    param($Entry)

    $cmd = $Entry.UninstallString
    if (-not $cmd) {
        return $false
    }

    Write-Step "正在调用安装程序自带的卸载器..."
    Write-Step "  $cmd"

    if ($cmd -match '^"(.+?)"\s*(.*)$') {
        $exe = $Matches[1]
        $args = $Matches[2]
    } elseif ($cmd -match '^(\S+)\s*(.*)$') {
        $exe = $Matches[1]
        $args = $Matches[2]
    } else {
        return $false
    }

    $silentArgs = if ($Silent) { "/SILENT /NORESTART /SUPPRESSMSGBOXES" } else { "/VERYSILENT /NORESTART /SUPPRESSMSGBOXES" }
    if ($args) {
        $allArgs = "$args $silentArgs".Trim()
    } else {
        $allArgs = $silentArgs
    }

    $proc = Start-Process -FilePath $exe -ArgumentList $allArgs -Wait -PassThru -WindowStyle Hidden
    if ($proc.ExitCode -ne 0) {
        Write-Step "[警告] 卸载器返回代码: $($proc.ExitCode)"
    }
    return $true
}

function Remove-ShortcutIfExists {
    param([string]$Path)
    if (Test-Path $Path) {
        Remove-Item -LiteralPath $Path -Force -ErrorAction SilentlyContinue
        Write-Step "[OK] 已删除快捷方式: $Path"
    }
}

function Remove-ManualInstall {
    param([string[]]$CandidateDirs)

    $removed = $false
    foreach ($dir in $CandidateDirs) {
        if (-not (Test-Path $dir)) {
            continue
        }
        Write-Step "正在删除目录: $dir"
        Remove-Item -LiteralPath $dir -Recurse -Force -ErrorAction SilentlyContinue
        if (-not (Test-Path $dir)) {
            Write-Step "[OK] 已删除: $dir"
            $removed = $true
        } else {
            Write-Step "[警告] 无法完全删除: $dir（可能被占用，请关闭程序后重试）"
        }
    }
    return $removed
}

function Remove-StartMenuFolder {
    $programs = [Environment]::GetFolderPath("CommonPrograms")
    $folder = Join-Path $programs $AppName
    if (Test-Path $folder) {
        Remove-Item -LiteralPath $folder -Recurse -Force -ErrorAction SilentlyContinue
        Write-Step "[OK] 已删除开始菜单文件夹"
    }
}

if (-not (Confirm-Uninstall)) {
    Write-Step "已取消卸载。"
    exit 0
}

Stop-AppProcess

$entry = Get-UninstallRegistryEntry
$uninstalled = $false

if ($entry) {
    $installLocation = $entry.InstallLocation
    if (Invoke-RegisteredUninstaller -Entry $entry) {
        $uninstalled = $true
        Start-Sleep -Seconds 2
        $stillThere = Get-UninstallRegistryEntry
        if ($stillThere) {
            Write-Step "[提示] 注册表中仍有安装记录，将尝试清理残留..."
        } else {
            Write-Step "[OK] 已通过卸载器完成卸载"
        }
    }
} else {
    Write-Step "[提示] 未找到安装版注册信息（可能是免安装版或已手动删除）"
}

$programFiles = ${env:ProgramFiles}
$programFilesX86 = ${env:ProgramFiles(x86)}
$candidateDirs = @(
    if ($entry -and $entry.InstallLocation) { $entry.InstallLocation.TrimEnd('\') } else { $null }
    (Join-Path $programFiles $DefaultFolder)
    if ($programFilesX86) { Join-Path $programFilesX86 $DefaultFolder } else { $null }
) | Where-Object { $_ -and $_.Length -gt 0 } | Select-Object -Unique

Remove-ManualInstall -CandidateDirs $candidateDirs | Out-Null
Remove-StartMenuFolder

$desktop = [Environment]::GetFolderPath("Desktop")
$publicDesktop = Join-Path $env:Public "Desktop"
Remove-ShortcutIfExists (Join-Path $desktop "$AppName.lnk")
Remove-ShortcutIfExists (Join-Path $publicDesktop "$AppName.lnk")
Remove-ShortcutIfExists (Join-Path $desktop "$ExeName.lnk")

Write-Host ""
Write-Step "========================================"
Write-Step " 卸载完成"
Write-Step "========================================"
Write-Step "现在可以运行新版本安装包 ScreenCaptureSetup.exe 进行安装。"
Write-Host ""

if (-not $Silent) {
    Read-Host "按 Enter 键退出"
}

exit 0
