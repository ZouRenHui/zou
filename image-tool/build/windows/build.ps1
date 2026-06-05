#Requires -Version 5.1
<#
.SYNOPSIS
  在 Windows 上一键构建 ImageTool.exe 与安装包 ImageToolSetup.exe

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\build\windows\build.ps1
#>
param(
    [switch]$SkipInstaller
)

$ErrorActionPreference = "Stop"

$BuildDir = $PSScriptRoot
$ProjectRoot = (Resolve-Path (Join-Path $BuildDir "..\..")).Path
$DistDir = Join-Path $ProjectRoot "dist\ImageTool"
$InstallerOut = Join-Path $ProjectRoot "installer\output"
$SpecFile = Join-Path $BuildDir "image_tool.spec"
$ReqWindows = Join-Path $ProjectRoot "requirements-windows.txt"
$ReqDefault = Join-Path $ProjectRoot "requirements.txt"

Write-Host "========================================"
Write-Host " 图片处理工具 — Windows 构建"
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

function Install-PaddlePaddle {
    param([string]$Python)

    Write-Host "安装 PaddlePaddle (CPU, Windows)..."
    $methods = @(
        @{ Args = @("-m", "pip", "install", "paddlepaddle>=3.0.0,<4.0.0") },
        @{ Args = @("-m", "pip", "install", "paddlepaddle==3.0.0", "-f", "https://www.paddlepaddle.org.cn/whl/windows/mkl/avx/stable.html") }
    )
    foreach ($method in $methods) {
        & $Python @($method.Args)
        if ($LASTEXITCODE -eq 0) {
            & $Python -c "import paddle; print('Paddle', paddle.__version__)"
            if ($LASTEXITCODE -eq 0) { return }
        }
        Write-Host "PaddlePaddle 安装方式失败，尝试下一种..."
    }
    throw "无法安装 PaddlePaddle，请检查网络或 Python 版本。"
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
$VenvPip = Join-Path $VenvDir "Scripts\pip.exe"

Write-Host ""
Write-Host "安装依赖..."
& $VenvPython -m pip install --upgrade pip wheel setuptools

$ReqFile = if (Test-Path $ReqWindows) { $ReqWindows } else { $ReqDefault }
Write-Host "使用依赖文件: $ReqFile"
& $VenvPython -m pip install -r $ReqFile
Install-PaddlePaddle -Python $VenvPython
& $VenvPython -m pip install -r (Join-Path $BuildDir "requirements-build.txt")

Write-Host ""
Write-Host "验证 Python 模块..."
Push-Location $ProjectRoot
try {
    & $VenvPython -c @"
import image_processing
import image_utils
import ocr_engines
import image_tool_gui
print('模块导入成功')
"@
    if ($LASTEXITCODE -ne 0) {
        throw "模块导入失败"
    }
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "正在打包 ImageTool.exe（含 PaddleOCR，可能需要 15~30 分钟）..."
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

$MainExe = Join-Path $DistDir "ImageTool.exe"
if (-not (Test-Path $MainExe)) {
    Write-Host "[错误] 未生成 $MainExe"
    exit 1
}
Write-Host "[OK] 已生成: $MainExe"

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

$SetupExe = Join-Path $InstallerOut "ImageToolSetup.exe"
if (-not (Test-Path $SetupExe)) {
    Write-Host "[错误] 未生成安装包: $SetupExe"
    exit 1
}

Write-Host ""
Write-Host "========================================"
Write-Host " 构建完成"
Write-Host "========================================"
Write-Host "程序:     $MainExe"
Write-Host "安装包:   $SetupExe"
