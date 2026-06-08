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
DOWNLOAD_README_SRC="$BUILD_DIR/KYLIN-DOWNLOAD-README.txt"
RUN_SCRIPT_SRC="$BUILD_DIR/run.sh"
CHECK_SCRIPT_SRC="$BUILD_DIR/check-kylin.sh"
ARCH_CHECK_SRC="$BUILD_DIR/arch-check.sh"
SHORTCUT_SCRIPT_SRC="$BUILD_DIR/install-shortcut.sh"
KYLIN_DETECT_SRC="$BUILD_DIR/kylin-detect.sh"
KYLIN_PYTHON_SRC="$BUILD_DIR/install-kylin-python.sh"
SYSTEM_DEPS_SRC="$BUILD_DIR/install-system-deps.sh"
DESKTOP_SHORTCUT_SRC="$BUILD_DIR/desktop-shortcut.sh"
PYTHON_LAUNCHER_SRC="$BUILD_DIR/python-launcher.sh"
REPAIR_MENU_SRC="$BUILD_DIR/repair-menu.sh"
GUI_DIALOG_SRC="$BUILD_DIR/gui-dialog.sh"
USER_GUIDE_SRC="$BUILD_DIR/使用说明.txt"
REPAIR_DESKTOP_SRC="$BUILD_DIR/一键修复-PDF工具箱.desktop"
LAUNCH_DESKTOP_SRC="$BUILD_DIR/打开-PDF工具箱.desktop"
UNINSTALL_SCRIPT_SRC="$BUILD_DIR/uninstall-kylin.sh"
SETUP_SCRIPT_SRC="$BUILD_DIR/setup-kylin.sh"
SETUP_DESKTOP_SRC="$BUILD_DIR/setup-kylin.desktop"

ARCH="$(uname -m)"
PORTABLE_TAR="PdfToWord-Kylin-${ARCH}.tar.gz"
PORTABLE_RUN="PdfToWord-Kylin-${ARCH}.run"
PORTABLE_TAR_PATH="$OUTPUT_DIR/$PORTABLE_TAR"
PORTABLE_RUN_PATH="$OUTPUT_DIR/$PORTABLE_RUN"

create_self_extractor() {
    local archive_path="$1"
    local tar_path="$2"

    cat > "$archive_path" << 'EOF'
#!/bin/bash
set -euo pipefail

APP_NAME="PDF 工具箱"
gui_info() {
    command -v zenity >/dev/null 2>&1 && zenity --info --title="$APP_NAME" --text="$1" --width=460 2>/dev/null || echo "$1"
}
gui_error() {
    command -v zenity >/dev/null 2>&1 && zenity --error --title="$APP_NAME" --text="$1" --width=460 2>/dev/null || echo "[错误] $1" >&2
}

MARKER="__ARCHIVE_BELOW__"
ARCHIVE_LINE=$(awk "/^${MARKER}\$/ { print NR + 1; exit }" "$0")
if [ -z "$ARCHIVE_LINE" ]; then
    gui_error "安装包格式错误。"
    exit 1
fi
INSTALL_BASE="${PDF_TOOLBOX_HOME:-$HOME/.local/share}"
INSTALL_DIR="$INSTALL_BASE/PdfToWord"
mkdir -p "$INSTALL_BASE"
tail -n "+${ARCHIVE_LINE}" "$0" | tar -xzf - -C "$INSTALL_BASE"
cd "$INSTALL_DIR"
chmod +x run.sh install-shortcut.sh install-kylin-python.sh install-system-deps.sh desktop-shortcut.sh python-launcher.sh repair-menu.sh gui-dialog.sh kylin-detect.sh 2>/dev/null || true

# 麒麟：一键安装 Python 模式（推荐，避免 libexpat 安全拦截）
if [ -f "./kylin-detect.sh" ]; then
    # shellcheck disable=SC1091
    source "./kylin-detect.sh"
    if is_kylin && [ -f "./install-kylin-python.sh" ] && [ -d "./app_source" ]; then
        ./install-kylin-python.sh
        exit 0
    fi
fi

# 非麒麟系统
chmod +x PdfToWord check-kylin.sh 2>/dev/null || true
./install-shortcut.sh
exec ./run.sh
exit 0
__ARCHIVE_BELOW__
EOF
    cat "$tar_path" >> "$archive_path"
    chmod +x "$archive_path"
}

echo "========================================"
echo " PDF 工具箱 — Linux / 麒麟 构建"
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
echo "正在打包免安装发布物..."
mkdir -p "$OUTPUT_DIR"

if [ -f "$README_SRC" ]; then
    cp "$README_SRC" "$DIST_DIR/README.txt"
fi
if [ -f "$RUN_SCRIPT_SRC" ]; then
    cp "$RUN_SCRIPT_SRC" "$DIST_DIR/run.sh"
    chmod +x "$DIST_DIR/run.sh"
fi
if [ -f "$CHECK_SCRIPT_SRC" ]; then
    cp "$CHECK_SCRIPT_SRC" "$DIST_DIR/check-kylin.sh"
    chmod +x "$DIST_DIR/check-kylin.sh"
fi
if [ -f "$ARCH_CHECK_SRC" ]; then
    cp "$ARCH_CHECK_SRC" "$DIST_DIR/arch-check.sh"
    chmod +x "$DIST_DIR/arch-check.sh"
fi
if [ -f "$SHORTCUT_SCRIPT_SRC" ]; then
    cp "$SHORTCUT_SCRIPT_SRC" "$DIST_DIR/install-shortcut.sh"
    chmod +x "$DIST_DIR/install-shortcut.sh"
fi
if [ -f "$KYLIN_DETECT_SRC" ]; then
    cp "$KYLIN_DETECT_SRC" "$DIST_DIR/kylin-detect.sh"
    chmod +x "$DIST_DIR/kylin-detect.sh"
fi
if [ -f "$KYLIN_PYTHON_SRC" ]; then
    cp "$KYLIN_PYTHON_SRC" "$DIST_DIR/install-kylin-python.sh"
    chmod +x "$DIST_DIR/install-kylin-python.sh"
fi
if [ -f "$SYSTEM_DEPS_SRC" ]; then
    cp "$SYSTEM_DEPS_SRC" "$DIST_DIR/install-system-deps.sh"
    chmod +x "$DIST_DIR/install-system-deps.sh"
fi
if [ -f "$DESKTOP_SHORTCUT_SRC" ]; then
    cp "$DESKTOP_SHORTCUT_SRC" "$DIST_DIR/desktop-shortcut.sh"
    chmod +x "$DIST_DIR/desktop-shortcut.sh"
fi
if [ -f "$PYTHON_LAUNCHER_SRC" ]; then
    cp "$PYTHON_LAUNCHER_SRC" "$DIST_DIR/python-launcher.sh"
    chmod +x "$DIST_DIR/python-launcher.sh"
fi
if [ -f "$REPAIR_MENU_SRC" ]; then
    cp "$REPAIR_MENU_SRC" "$DIST_DIR/repair-menu.sh"
    chmod +x "$DIST_DIR/repair-menu.sh"
    cp "$REPAIR_MENU_SRC" "$OUTPUT_DIR/repair-menu.sh"
    chmod +x "$OUTPUT_DIR/repair-menu.sh"
fi
if [ -f "$GUI_DIALOG_SRC" ]; then
    cp "$GUI_DIALOG_SRC" "$DIST_DIR/gui-dialog.sh"
    chmod +x "$DIST_DIR/gui-dialog.sh"
    cp "$GUI_DIALOG_SRC" "$OUTPUT_DIR/gui-dialog.sh"
    chmod +x "$OUTPUT_DIR/gui-dialog.sh"
fi
if [ -f "$USER_GUIDE_SRC" ]; then
    cp "$USER_GUIDE_SRC" "$OUTPUT_DIR/使用说明.txt"
fi
if [ -f "$REPAIR_DESKTOP_SRC" ]; then
    cp "$REPAIR_DESKTOP_SRC" "$OUTPUT_DIR/一键修复-PDF工具箱.desktop"
    chmod +x "$OUTPUT_DIR/一键修复-PDF工具箱.desktop"
fi
if [ -f "$LAUNCH_DESKTOP_SRC" ]; then
    cp "$LAUNCH_DESKTOP_SRC" "$OUTPUT_DIR/打开-PDF工具箱.desktop"
    chmod +x "$OUTPUT_DIR/打开-PDF工具箱.desktop"
fi

# 远程用户修复包（解压后双击「一键修复」即可，无需命令行）
REPAIR_ZIP="$OUTPUT_DIR/PdfToWord-修复包-${ARCH}.zip"
if command -v zip >/dev/null 2>&1 && [ -f "$REPAIR_MENU_SRC" ]; then
    rm -f "$REPAIR_ZIP"
    (
        cd "$BUILD_DIR"
        zip -q "$REPAIR_ZIP" \
            repair-menu.sh gui-dialog.sh python-launcher.sh desktop-shortcut.sh \
            一键修复-PDF工具箱.desktop 打开-PDF工具箱.desktop 使用说明.txt
    )
    echo "[OK] 修复包: $REPAIR_ZIP"
fi

echo "打包 Python 源码（麒麟安全模式）..."
SOURCE_DIR="$DIST_DIR/app_source"
mkdir -p "$SOURCE_DIR"
for f in pdf_to_word_gui.py pdf_to_word.py pdf_tools.py office_to_pdf.py requirements.txt; do
    cp "$PROJECT_ROOT/$f" "$SOURCE_DIR/"
done

rm -f "$PORTABLE_TAR_PATH" "$PORTABLE_RUN_PATH"
tar -czf "$PORTABLE_TAR_PATH" -C "$PROJECT_ROOT/dist" PdfToWord
echo "[OK] tar.gz: $PORTABLE_TAR_PATH"

create_self_extractor "$PORTABLE_RUN_PATH" "$PORTABLE_TAR_PATH"
echo "[OK] 自解压: $PORTABLE_RUN_PATH"

if [ -f "$DOWNLOAD_README_SRC" ]; then
    cp "$DOWNLOAD_README_SRC" "$OUTPUT_DIR/KYLIN-DOWNLOAD-README.txt"
fi
if [ -f "$SETUP_SCRIPT_SRC" ]; then
    cp "$SETUP_SCRIPT_SRC" "$OUTPUT_DIR/setup-kylin.sh"
    chmod +x "$OUTPUT_DIR/setup-kylin.sh"
fi
if [ -f "$UNINSTALL_SCRIPT_SRC" ]; then
    cp "$UNINSTALL_SCRIPT_SRC" "$OUTPUT_DIR/uninstall-kylin.sh"
    chmod +x "$OUTPUT_DIR/uninstall-kylin.sh"
fi
if [ -f "$SETUP_DESKTOP_SRC" ]; then
    cp "$SETUP_DESKTOP_SRC" "$OUTPUT_DIR/setup-kylin.desktop"
    chmod +x "$OUTPUT_DIR/setup-kylin.desktop"
fi
INSTALL_DESKTOP_SRC="$BUILD_DIR/install-aarch64.desktop"
if [ -f "$INSTALL_DESKTOP_SRC" ] && [ "$ARCH" = "aarch64" ]; then
    cp "$INSTALL_DESKTOP_SRC" "$OUTPUT_DIR/一键安装-PDF工具箱.desktop"
    chmod +x "$OUTPUT_DIR/一键安装-PDF工具箱.desktop"
fi

echo ""
echo "========================================"
echo " 构建完成"
echo "========================================"
echo "程序目录: $DIST_DIR"
echo "tar.gz:    $PORTABLE_TAR_PATH"
echo "自解压:    $PORTABLE_RUN_PATH  ← 麒麟推荐"
echo ""
echo "麒麟用户推荐: chmod +x PdfToWord-Kylin-${ARCH}.run && ./PdfToWord-Kylin-${ARCH}.run"
