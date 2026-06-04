#Requires -Version 5.1
<#
.SYNOPSIS
  在 Windows 上一键构建 PdfToWord.exe 与安装包 PdfToWordSetup.exe

.DESCRIPTION
  1. 检测本机 Python
  2. 安装项目依赖与 PyInstaller
  3. 打包 GUI 为 dist\PdfToWord\PdfToWord.exe
  4. 使用 Inno Setup 生成 installer\output\PdfToWordSetup.exe

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\build\windows\build.ps1
#>
param(
    [switch]$SkipInstaller,
    [switch]$SkipVcCheck
)

$ErrorActionPreference = "Stop"

$BuildDir = $PSScriptRoot
$ProjectRoot = (Resolve-Path (Join-Path $BuildDir "..\..")).Path
$DistDir = Join-Path $ProjectRoot "dist\PdfToWord"
$InstallerOut = Join-Path $ProjectRoot "installer\output"
$SpecFile = Join-Path $BuildDir "pdf_to_word.spec"

Write-Host "========================================"
Write-Host " PDF 转 Word — Windows 构建"
Write-Host "========================================"
Write-Host "项目目录: $ProjectRoot"
Write-Host ""

# --- Python ---
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
    Write-Host "[错误] 未找到 Python 3.9+。"
    Write-Host ""
    Write-Host "构建机需要先安装 Python。正在尝试通过 winget 安装..."
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if ($winget) {
        & winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
        $PythonExe = Find-Python
    }
    if (-not $PythonExe) {
        Write-Host "请手动安装 Python 3.9+ 后重试: https://www.python.org/downloads/"
        Write-Host "安装时勾选「Add python.exe to PATH」。"
        exit 1
    }
}

Write-Host "[OK] Python: $PythonExe"
& $PythonExe --version

# --- 虚拟环境与依赖 ---
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
& $VenvPip install --upgrade pip -q
& $VenvPip install -r (Join-Path $ProjectRoot "requirements.txt") -q
& $VenvPip install -r (Join-Path $BuildDir "requirements-build.txt") -q

# --- PyInstaller ---
Write-Host ""
Write-Host "正在打包 PdfToWord.exe（可能需要几分钟）..."
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

$MainExe = Join-Path $DistDir "PdfToWord.exe"
if (-not (Test-Path $MainExe)) {
    Write-Host "[错误] 未生成 $MainExe"
    exit 1
}
Write-Host "[OK] 已生成: $MainExe"

if ($SkipInstaller) {
    Write-Host ""
    Write-Host "已跳过安装包构建（-SkipInstaller）。"
    Write-Host "可直接运行: $MainExe"
    exit 0
}

# --- Inno Setup ---
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
    Write-Host "[提示] 未安装 Inno Setup，无法生成安装程序。"
    Write-Host "请安装: https://jrsoftware.org/isdl.php"
    Write-Host "或使用 winget: winget install JRSoftware.InnoSetup"
    Write-Host ""
    Write-Host "已生成的可执行文件可直接使用: $MainExe"
    exit 0
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

$SetupExe = Join-Path $InstallerOut "PdfToWordSetup.exe"
Write-Host ""
if (Test-Path $SetupExe) {
    Write-Host "========================================"
    Write-Host " 构建完成"
    Write-Host "========================================"
    Write-Host "程序:     $MainExe"
    Write-Host "安装包:   $SetupExe"
    Write-Host ""
    Write-Host "将 PdfToWordSetup.exe 分发给用户，双击安装后即可从开始菜单或桌面启动。"
} else {
    Write-Host "[错误] 未生成安装包: $SetupExe"
    exit 1
}
