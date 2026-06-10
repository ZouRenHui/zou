#Requires -Version 5.1
<#
.SYNOPSIS
  在 Windows 上一键构建 ScreenCapture.exe、免安装 zip 与安装包 ScreenCaptureSetup.exe

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\build\windows\build.ps1
#>
param(
    [switch]$SkipInstaller
)

$ErrorActionPreference = "Stop"

$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

$BuildDir = $PSScriptRoot
$ProjectRoot = (Resolve-Path (Join-Path $BuildDir "..\..")).Path
$DistDir = Join-Path $ProjectRoot "dist\ScreenCapture"
$InstallerOut = Join-Path $ProjectRoot "installer\output"
$SpecFile = Join-Path $BuildDir "screen_capture.spec"
$PortableZip = Join-Path $InstallerOut "ScreenCapture-Portable.zip"
$PortableReadme = Join-Path $BuildDir "PORTABLE-README.txt"
$ReqWindows = Join-Path $ProjectRoot "requirements-windows.txt"
$ReqDefault = Join-Path $ProjectRoot "requirements.txt"

function New-PortablePackage {
    param(
        [string]$SourceDir,
        [string]$ZipPath,
        [string]$ReadmeSource
    )

    if (-not (Test-Path $SourceDir)) {
        throw "未找到程序目录: $SourceDir"
    }

    $outDir = Split-Path $ZipPath -Parent
    New-Item -ItemType Directory -Force -Path $outDir | Out-Null

    if (Test-Path $ReadmeSource) {
        Copy-Item $ReadmeSource (Join-Path $SourceDir "使用说明.txt") -Force
    }

    if (Test-Path $ZipPath) {
        Remove-Item $ZipPath -Force
    }

    Compress-Archive -Path $SourceDir -DestinationPath $ZipPath -CompressionLevel Optimal -Force
    return $ZipPath
}

Write-Host "========================================"
Write-Host " 录屏/截屏工具 — Windows 构建"
Write-Host "========================================"
Write-Host "项目目录: $ProjectRoot"
if ($env:GITHUB_ACTIONS -eq "true") {
    Write-Host "运行环境: GitHub Actions"
}
Write-Host ""

function Find-Python {
    $candidates = @("python", "python3", "py")
    foreach ($name in $candidates) {
        try {
            $exe = (Get-Command $name -ErrorAction Stop).Source
            $ver = & $exe -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
            $parts = $ver.Split(".")
            $major = [int]$parts[0]
            $minor = [int]$parts[1]
            if ($major -ge 3 -and $minor -ge 9) {
                return $exe
            }
        } catch {
            continue
        }
    }
    return $null
}

$PythonExe = Find-Python
if (-not $PythonExe) {
    if ($env:GITHUB_ACTIONS -eq "true") {
        Write-Host "[错误] GitHub Actions 上未找到 Python，请检查 setup-python 步骤。"
        exit 1
    }
    Write-Host "[错误] 未找到 Python 3.9+。"
    Write-Host "正在尝试通过 winget 安装..."
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if ($winget) {
        & winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
        $PythonExe = Find-Python
    }
    if (-not $PythonExe) {
        Write-Host "请手动安装 Python 3.9+ 后重试: https://www.python.org/downloads/"
        exit 1
    }
}

Write-Host "[OK] Python: $PythonExe"
& $PythonExe --version

$VenvDir = Join-Path $ProjectRoot ".venv-build"
if (-not (Test-Path (Join-Path $VenvDir "Scripts\python.exe"))) {
    Write-Host ""
    Write-Host "创建构建虚拟环境..."
    & $PythonExe -m venv $VenvDir
}

$VenvPython = Join-Path $VenvDir "Scripts\python.exe"

Write-Host ""
Write-Host "安装依赖..."
& $VenvPython -m pip install --upgrade pip wheel setuptools

$ReqFile = if (Test-Path $ReqWindows) { $ReqWindows } else { $ReqDefault }
Write-Host "使用依赖文件: $ReqFile"
& $VenvPython -m pip install -r $ReqFile
& $VenvPython -m pip install -r (Join-Path $BuildDir "requirements-build.txt")

Write-Host ""
Write-Host "Verifying Python modules..."
$env:PYTHONPATH = $ProjectRoot
Push-Location $ProjectRoot
try {
    & $VenvPython (Join-Path $BuildDir "verify_imports.py")
    if ($LASTEXITCODE -ne 0) {
        throw "Module import verification failed."
    }
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "正在打包 ScreenCapture.exe（可能需要几分钟）..."
Push-Location $ProjectRoot
try {
    $DistPath = Join-Path $ProjectRoot "dist"
    $WorkPath = Join-Path $ProjectRoot "build\pyinstaller"
    & (Join-Path $VenvDir "Scripts\pyinstaller.exe") $SpecFile --noconfirm --clean --distpath $DistPath --workpath $WorkPath
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[错误] PyInstaller 打包失败，退出码: $LASTEXITCODE"
        exit 1
    }
} finally {
    Pop-Location
}

$MainExe = Join-Path $DistDir "ScreenCapture.exe"
if (-not (Test-Path $MainExe)) {
    Write-Host "[错误] 未生成 $MainExe"
    exit 1
}
Write-Host "[OK] 已生成: $MainExe"

Write-Host ""
Write-Host "正在打包免安装版..."
New-PortablePackage -SourceDir $DistDir -ZipPath $PortableZip -ReadmeSource $PortableReadme | Out-Null
Write-Host "[OK] 免安装包: $PortableZip"

if ($SkipInstaller) {
    Write-Host ""
    Write-Host "已跳过安装包构建（-SkipInstaller）。"
    exit 0
}

$IsccPaths = @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
)
$Iscc = $null
foreach ($p in $IsccPaths) {
    if (Test-Path $p) { $Iscc = $p; break }
}

if (-not $Iscc) {
    Write-Host ""
    Write-Host "[错误] 未找到 Inno Setup 6（生成安装包必需）。"
    Write-Host "请安装: winget install JRSoftware.InnoSetup"
    exit 1
}

New-Item -ItemType Directory -Force -Path $InstallerOut | Out-Null
$IssFile = Join-Path $ProjectRoot "installer\setup.iss"

Write-Host ""
Write-Host "正在编译安装包..."
& $Iscc $IssFile
if ($LASTEXITCODE -ne 0) {
    Write-Host "[错误] Inno Setup 编译失败，退出码: $LASTEXITCODE"
    exit 1
}

$SetupExe = Join-Path $InstallerOut "ScreenCaptureSetup.exe"
if (-not (Test-Path $SetupExe)) {
    Write-Host "[错误] 未生成安装包: $SetupExe"
    exit 1
}

Write-Host ""
Write-Host "========================================"
Write-Host " 构建完成"
Write-Host "========================================"
Write-Host "程序:       $MainExe"
Write-Host "免安装包:   $PortableZip"
Write-Host "安装包:     $SetupExe"
