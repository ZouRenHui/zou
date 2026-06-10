#Requires -Version 5.1
<#
.SYNOPSIS
  安装前自动检测环境，并下载安装缺失的 VC++ 运行库等依赖。
#>
param(
    [switch]$SkipVcRedist
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$CheckScript = Join-Path $ScriptDir "check-environment.ps1"

Write-Host "========================================"
Write-Host " 录屏/截屏工具 — 环境检测"
Write-Host "========================================"
Write-Host ""

& $CheckScript
$checkExit = $LASTEXITCODE

function Test-VcRedistInstalled {
    $vcKeys = @(
        "HKLM:\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64",
        "HKLM:\SOFTWARE\WOW6432Node\Microsoft\VisualStudio\14.0\VC\Runtimes\x64"
    )
    foreach ($key in $vcKeys) {
        if (Test-Path $key) {
            $installed = (Get-ItemProperty -Path $key -ErrorAction SilentlyContinue).Installed
            if ($installed -eq 1) { return $true }
        }
    }
    return $false
}

if ($SkipVcRedist) {
    Write-Host "已跳过 VC++ 运行库安装。"
    exit 0
}

if (Test-VcRedistInstalled) {
    Write-Host "VC++ 运行库已存在，无需下载。"
    exit 0
}

Write-Host ""
Write-Host "正在下载 Visual C++ 2015-2022 运行库 (x64)..."

$vcUrl = "https://aka.ms/vs/17/release/vc_redist.x64.exe"
$tempDir = Join-Path $env:TEMP "ScreenCaptureSetup"
New-Item -ItemType Directory -Force -Path $tempDir | Out-Null
$installerPath = Join-Path $tempDir "vc_redist.x64.exe"

try {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -Uri $vcUrl -OutFile $installerPath -UseBasicParsing
} catch {
    Write-Host "下载失败: $_"
    Write-Host "请手动安装: $vcUrl"
    exit 1
}

Write-Host "正在安装 VC++ 运行库（可能需要管理员权限）..."
$proc = Start-Process -FilePath $installerPath -ArgumentList "/install", "/quiet", "/norestart" -Wait -PassThru

if ($proc.ExitCode -ne 0 -and $proc.ExitCode -ne 1638) {
    Write-Host "VC++ 安装返回代码: $($proc.ExitCode)"
    if (-not (Test-VcRedistInstalled)) {
        Write-Host "自动安装可能未成功，请手动运行: $installerPath"
        exit 1
    }
}

if (Test-VcRedistInstalled) {
    Write-Host "VC++ 运行库安装完成。"
} else {
    Write-Host "警告: 未能确认 VC++ 安装状态，若程序无法启动请手动安装运行库。"
}

exit 0
