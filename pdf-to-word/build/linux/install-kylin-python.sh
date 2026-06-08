#!/usr/bin/env bash
# 麒麟系统 Python 源码模式安装（避免 PyInstaller 自带 libexpat.so 触发安全拦截）
set -euo pipefail

APP_NAME="PDF 工具箱"
APP_ID="pdf-toolbox"
INSTALL_ROOT="${PDF_TOOLBOX_INSTALL:-$HOME/.local/share/pdf-to-word}"
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="$APP_DIR/app_source"
VENV_DIR="$INSTALL_ROOT/venv"
LAUNCHER="$INSTALL_ROOT/run-python.sh"
MENU_DIR="${HOME}/.local/share/applications"
DESKTOP_NAMES=("Desktop" "桌面")

SHORTCUT_ONLY=false
if [ "${1:-}" = "--shortcut-only" ]; then
    SHORTCUT_ONLY=true
fi

# shellcheck disable=SC1091
source "$APP_DIR/kylin-detect.sh" 2>/dev/null || true

if [ ! -d "$SOURCE_DIR" ]; then
    echo "[错误] 未找到 app_source 源码目录: $SOURCE_DIR"
    exit 1
fi

install_deps() {
    echo "正在安装系统依赖（需要联网）..."
    if command -v apt-get >/dev/null 2>&1; then
        sudo apt-get update
        sudo apt-get install -y python3 python3-pip python3-venv python3-tk libreoffice 2>/dev/null || \
        sudo apt-get install -y python3 python3-pip python3-venv python3-tk
    elif command -v dnf >/dev/null 2>&1; then
        sudo dnf install -y python3 python3-pip python3-tkinter libreoffice 2>/dev/null || \
        sudo dnf install -y python3 python3-pip python3-tkinter
    elif command -v yum >/dev/null 2>&1; then
        sudo yum install -y python3 python3-pip python3-tkinter
    fi
}

setup_app() {
    echo "安装 Python 版到: $INSTALL_ROOT"
    mkdir -p "$INSTALL_ROOT/app"
    rm -rf "$INSTALL_ROOT/app"
    cp -a "$SOURCE_DIR/." "$INSTALL_ROOT/app/"

    if [ ! -d "$VENV_DIR" ]; then
        python3 -m venv "$VENV_DIR"
    fi

    # shellcheck disable=SC1091
    source "$VENV_DIR/bin/activate"
    python -m pip install --upgrade pip
    python -m pip install -r "$INSTALL_ROOT/app/requirements.txt"

    cat > "$LAUNCHER" <<EOF
#!/usr/bin/env bash
source "$VENV_DIR/bin/activate"
exec python "$INSTALL_ROOT/app/pdf_to_word_gui.py" "\$@"
EOF
    chmod +x "$LAUNCHER"
    echo "[OK] 启动脚本: $LAUNCHER"
}

create_shortcuts() {
    mkdir -p "$MENU_DIR"

    DESKTOP_CONTENT="[Desktop Entry]
Version=1.0
Type=Application
Name=${APP_NAME}
Name[zh_CN]=${APP_NAME}
Comment=PDF 转 Word、拼接、拆分（Python 模式，适配麒麟安全）
Comment[zh_CN]=PDF 转 Word、拼接、拆分
Exec=${LAUNCHER}
Path=${INSTALL_ROOT}
Icon=application-pdf
Terminal=false
Categories=Office;Utility;
StartupNotify=true
X-Kylin-PDF-Toolbox-Mode=python
"

    MENU_FILE="${MENU_DIR}/${APP_ID}.desktop"
    printf '%s' "$DESKTOP_CONTENT" > "$MENU_FILE"
    chmod +x "$MENU_FILE"

    for name in "${DESKTOP_NAMES[@]}"; do
        desk="${HOME}/${name}"
        if [ -d "$desk" ]; then
            cp "$MENU_FILE" "${desk}/${APP_ID}.desktop"
            chmod +x "${desk}/${APP_ID}.desktop"
            echo "[OK] 桌面快捷方式: ${desk}/${APP_ID}.desktop"
            break
        fi
    done

    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database "$MENU_DIR" 2>/dev/null || true
    fi
}

if ! $SHORTCUT_ONLY; then
    if ! python3 -c "import tkinter" 2>/dev/null; then
        install_deps
    fi
    if ! python3 -c "import tkinter" 2>/dev/null; then
        echo "[错误] tkinter 不可用，请安装: sudo apt install python3-tk"
        exit 1
    fi
    setup_app
fi

if [ ! -x "$LAUNCHER" ]; then
    echo "[错误] 未找到 $LAUNCHER，请先完整运行 install-kylin-python.sh"
    exit 1
fi

create_shortcuts

echo ""
echo "========================================"
echo " 麒麟 Python 模式安装完成"
echo "========================================"
echo "说明: 桌面快捷方式已改为系统 Python 启动，"
echo "      可避免 libexpat.so 未认证拦截问题。"
echo ""
echo "启动: $LAUNCHER"
echo "或在应用菜单搜索「${APP_NAME}」"
