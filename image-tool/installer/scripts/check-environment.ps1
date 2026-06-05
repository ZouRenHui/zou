#Requires -Version 5.1
<#
.SYNOPSIS
  检测 Windows 运行环境是否满足图片处理工具要求。
#>
param(
    [int]$MinFreeDiskMB = 2048
)

$ErrorActionPreference = "Stop"

function Write-Check([string]$Name, [bool]$Ok, [string]$Detail) {
    $mark = if ($Ok) { "[OK]" } else { "[FAIL]" }
    Write-Host "$mark $Name — $Detail"
    if (-not $Ok) { $script:AllOk = $false }
}

$AllOk = $true

$os = Get-CimInstance Win32_OperatingSystem
$build = [int]$os.BuildNumber
$win10Plus = $build -ge 10240
Write-Check "Windows 版本" $win10Plus "$($os.Caption) (Build $build)"

$is64 = [Environment]::Is64BitOperatingSystem
Write-Check "系统架构" $is64 "需要 64 位 Windows"

$drive = "C"
$vol = Get-PSDrive -Name $drive -ErrorAction SilentlyContinue
if ($vol) {
    $freeMb = [math]::Round($vol.Free / 1MB)
    Write-Check "磁盘空间 ($drive`:)" ($freeMb -ge $MinFreeDiskMB) "${freeMb} MB 可用（建议 >= ${MinFreeDiskMB} MB，含 OCR 模型缓存）"
}

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
Write-Check "VC++ 运行库 (x64)" $true $(if ($vcInstalled) { "已安装" } else { "未检测到，安装程序将尝试自动安装" })

function Test-TesseractPresent {
    $paths = @(
        "${env:ProgramFiles}\Tesseract-OCR\tesseract.exe",
        "${env:ProgramFiles(x86)}\Tesseract-OCR\tesseract.exe"
    )
    foreach ($p in $paths) {
        if (Test-Path $p) { return $true }
    }
    return $null -ne (Get-Command tesseract -ErrorAction SilentlyContinue)
}

$tessOk = Test-TesseractPresent
Write-Check "Tesseract OCR" $true $(if ($tessOk) { "已安装（可选用 Tesseract 识别引擎）" } else { "未检测到，安装程序将尝试自动安装（可选引擎）" })

if (-not $AllOk) {
    Write-Host ""
    Write-Host "环境检测未完全通过。请根据上述提示处理后再继续安装。"
    exit 1
}

Write-Host ""
Write-Host "环境检测通过。"
Write-Host "说明: 默认使用 PaddleOCR，首次识别需联网下载模型（约数百 MB）。"
exit 0
