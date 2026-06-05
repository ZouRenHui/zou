#Requires -Version 5.1
<#
.SYNOPSIS
  安装后自动检测环境，并下载安装缺失的 VC++ 运行库、Tesseract OCR 等依赖。
#>
param(
    [switch]$SkipVcRedist,
    [switch]$SkipTesseract
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$CheckScript = Join-Path $ScriptDir "check-environment.ps1"

Write-Host "========================================"
Write-Host " 图片处理工具 — 环境检测与依赖安装"
Write-Host "========================================"
Write-Host ""

& $CheckScript
if ($LASTEXITCODE -ne 0) {
    Write-Host "部分环境项未通过，仍将尝试安装缺失的运行库..."
}

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

function Test-TesseractInstalled {
    $paths = @(
        "${env:ProgramFiles}\Tesseract-OCR\tesseract.exe",
        "${env:ProgramFiles(x86)}\Tesseract-OCR\tesseract.exe"
    )
    foreach ($p in $paths) {
        if (Test-Path $p) { return $true }
    }
    return $null -ne (Get-Command tesseract -ErrorAction SilentlyContinue)
}

function Install-VcRedist {
    if ($SkipVcRedist) {
        Write-Host "已跳过 VC++ 运行库安装。"
        return
    }
    if (Test-VcRedistInstalled) {
        Write-Host "VC++ 运行库已存在，无需下载。"
        return
    }

    Write-Host ""
    Write-Host "正在下载 Visual C++ 2015-2022 运行库 (x64)..."
    $vcUrl = "https://aka.ms/vs/17/release/vc_redist.x64.exe"
    $tempDir = Join-Path $env:TEMP "ImageToolSetup"
    New-Item -ItemType Directory -Force -Path $tempDir | Out-Null
    $installerPath = Join-Path $tempDir "vc_redist.x64.exe"

    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -Uri $vcUrl -OutFile $installerPath -UseBasicParsing
    } catch {
        Write-Host "下载失败: $_"
        Write-Host "请手动安装: $vcUrl"
        return
    }

    Write-Host "正在安装 VC++ 运行库..."
    $proc = Start-Process -FilePath $installerPath -ArgumentList "/install", "/quiet", "/norestart" -Wait -PassThru
    if ($proc.ExitCode -ne 0 -and $proc.ExitCode -ne 1638) {
        Write-Host "VC++ 安装返回代码: $($proc.ExitCode)"
    }
    if (Test-VcRedistInstalled) {
        Write-Host "VC++ 运行库安装完成。"
    } else {
        Write-Host "警告: 未能确认 VC++ 安装状态，若程序无法启动请手动安装运行库。"
    }
}

function Install-Tesseract {
    if ($SkipTesseract) {
        Write-Host "已跳过 Tesseract OCR 安装。"
        return
    }
    if (Test-TesseractInstalled) {
        Write-Host "Tesseract OCR 已存在，无需安装。"
        return
    }

    Write-Host ""
    Write-Host "正在安装 Tesseract OCR（Tesseract 识别引擎需要）..."

    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if ($winget) {
        try {
            $proc = Start-Process -FilePath "winget" -ArgumentList @(
                "install", "-e", "--id", "UB-Mannheim.TesseractOCR",
                "--accept-package-agreements", "--accept-source-agreements",
                "--silent"
            ) -Wait -PassThru -NoNewWindow
            if ($proc.ExitCode -eq 0 -or (Test-TesseractInstalled)) {
                Write-Host "Tesseract OCR 已通过 winget 安装。"
                return
            }
            Write-Host "winget 安装返回代码: $($proc.ExitCode)，尝试下载安装包..."
        } catch {
            Write-Host "winget 安装失败: $_"
        }
    }

    $tessUrl = "https://digi.bib.uni-mannheim.de/tesseract/tesseract-ocr-w64-setup-5.5.0.20241111.exe"
    $tempDir = Join-Path $env:TEMP "ImageToolSetup"
    New-Item -ItemType Directory -Force -Path $tempDir | Out-Null
    $installerPath = Join-Path $tempDir "tesseract-setup.exe"

    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -Uri $tessUrl -OutFile $installerPath -UseBasicParsing
    } catch {
        Write-Host "Tesseract 下载失败: $_"
        Write-Host "请手动安装: https://github.com/UB-Mannheim/tesseract/wiki"
        return
    }

    Write-Host "正在运行 Tesseract 安装程序（静默安装）..."
    $proc = Start-Process -FilePath $installerPath -ArgumentList "/VERYSILENT", "/NORESTART", "/SUPPRESSMSGBOXES" -Wait -PassThru
    if (Test-TesseractInstalled) {
        Write-Host "Tesseract OCR 安装完成。"
    } else {
        Write-Host "警告: 未能确认 Tesseract 安装。使用 Tesseract 引擎时请手动安装并加入 PATH。"
        Write-Host "下载地址: https://github.com/UB-Mannheim/tesseract/wiki"
    }
}

Install-VcRedist
Install-Tesseract

Write-Host ""
Write-Host "依赖安装流程结束。"
exit 0
