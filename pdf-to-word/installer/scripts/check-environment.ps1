#Requires -Version 5.1
<#
.SYNOPSIS
  检测 Windows 运行环境是否满足 PDF 转 Word 工具要求。
#>
param(
    [int]$MinFreeDiskMB = 300
)

$ErrorActionPreference = "Stop"

function Write-Check([string]$Name, [bool]$Ok, [string]$Detail) {
    $mark = if ($Ok) { "[OK]" } else { "[FAIL]" }
    Write-Host "$mark $Name — $Detail"
    if (-not $Ok) { $script:AllOk = $false }
}

$AllOk = $true

# 系统版本
$os = Get-CimInstance Win32_OperatingSystem
$build = [int]$os.BuildNumber
$win10Plus = $build -ge 10240
Write-Check "Windows 版本" $win10Plus "$($os.Caption) (Build $build)"

# 64 位
$is64 = [Environment]::Is64BitOperatingSystem
Write-Check "系统架构" $is64 "需要 64 位 Windows"

# 磁盘空间（安装目标盘，默认 C:）
$drive = (Get-Location).Drive.Name
if (-not $drive) { $drive = "C" }
$vol = Get-PSDrive -Name $drive -ErrorAction SilentlyContinue
if ($vol) {
    $freeMb = [math]::Round($vol.Free / 1MB)
    Write-Check "磁盘空间 ($drive`:)" ($freeMb -ge $MinFreeDiskMB) "${freeMb} MB 可用（需要 >= ${MinFreeDiskMB} MB）"
}

# Visual C++ 2015-2022 x64 运行库（PyInstaller / PyMuPDF 常用）
$vcKeys = @(
    "HKLM:\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64",
    "HKLM:\SOFTWARE\WOW6432Node\Microsoft\VisualStudio\14.0\VC\Runtimes\x64"
)
$vcInstalled = $false
foreach ($key in $vcKeys) {
    if (Test-Path $key) {
        $installed = (Get-ItemProperty -Path $key -ErrorAction SilentlyContinue).Installed
        if ($installed -eq 1) {
            $vcInstalled = $true
            break
        }
    }
}
# 缺失时由安装脚本自动补装，不视为阻断项
Write-Check "VC++ 运行库 (x64)" $true $(if ($vcInstalled) { "已安装" } else { "未检测到，安装程序将尝试自动安装" })

if (-not $AllOk) {
    Write-Host ""
    Write-Host "环境检测未完全通过。请根据上述提示处理后再继续安装。"
    exit 1
}

Write-Host ""
Write-Host "环境检测通过。"
exit 0
