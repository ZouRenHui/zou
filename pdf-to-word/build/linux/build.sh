#!/usr/bin/env bash
# 在 Linux / 麒麟系统上构建免安装包
set -euo pipefail

BUILD_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$BUILD_DIR/../.." && pwd)"
DIST_DIR="$PROJECT_ROOT/dist/PdfToWord"
OUTPUT_DIR="$PROJECT_ROOT/installer/output"
SPEC_FILE="$BUILD_DIR/pdf_to_word.spec"
VENV_DIR="$PROJECT_ROOT/.venv-build-linux"
README_SRC="$BUILD_DIR/KYLIN-README.txt"
RUN_SCRIPT_SRC="$BUILD_DIR/run.sh"

ARCH="$(uname -m)"
PORTABLE_NAME="PdfToWord-Kylin-${ARCH}.tar.gz"
PORTABLE_PATH="$OUTPUT_DIR/$PORTABLE_NAME"

echo "========================================"
echo " PDF 转 Word — Linux / 麒麟 构建"
echo "========================================"
echo "项目目录: $PROJECT_ROOT"
echo "目标架构: $ARCH"
echo ""

if ! command -v python3 >/dev/null 2>&1; then
    echo "[错误] 未找到 python3，请先安装 Python 3.9+"
    exit 1
fi

PY_VER="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
PY_MAJOR="${PY_VER%%.*}"
PY_MINOR="${PY_VER#*.}"
if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 9 ]; }; then
    echo "[错误] 需要 Python 3.9+，当前: $PY_VER"
    exit 1
fi

echo "[OK] Python $PY_VER"

if [ ! -d "$VENV_DIR" ]; then
    echo ""
    echo "创建构建虚拟环境..."
    python3 -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo ""
echo "安装依赖..."
python -m pip install --upgrade pip
python -m pip install -r "$PROJECT_ROOT/requirements.txt"
python -m pip install -r "$BUILD_DIR/requirements-build.txt"

echo ""
echo "正在打包 PdfToWord（可能需要几分钟）..."
mkdir -p "$PROJECT_ROOT/dist" "$PROJECT_ROOT/build/pyinstaller-linux"
pyinstaller "$SPEC_FILE" \
    --noconfirm \
    --clean \
    --distpath "$PROJECT_ROOT/dist" \
    --workpath "$PROJECT_ROOT/build/pyinstaller-linux"

MAIN_BIN="$DIST_DIR/PdfToWord"
if [ ! -f "$MAIN_BIN" ]; then
    echo "[错误] 未生成 $MAIN_BIN"
    exit 1
fi
chmod +x "$MAIN_BIN"
echo "[OK] 已生成: $MAIN_BIN"

echo ""
echo "正在打包免安装压缩包..."
mkdir -p "$OUTPUT_DIR"

if [ -f "$README_SRC" ]; then
    cp "$README_SRC" "$DIST_DIR/使用说明.txt"
fi
if [ -f "$RUN_SCRIPT_SRC" ]; then
    cp "$RUN_SCRIPT_SRC" "$DIST_DIR/run.sh"
    chmod +x "$DIST_DIR/run.sh"
fi

rm -f "$PORTABLE_PATH"
tar -czf "$PORTABLE_PATH" -C "$PROJECT_ROOT/dist" PdfToWord

echo ""
echo "========================================"
echo " 构建完成"
echo "========================================"
echo "程序目录: $DIST_DIR"
echo "免安装包: $PORTABLE_PATH"
echo ""
echo "分发免安装包给用户：解压后执行 ./run.sh 或 ./PdfToWord"
