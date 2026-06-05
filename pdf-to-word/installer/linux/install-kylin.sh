#!/usr/bin/env bash
# 麒麟 / Linux 脚本安装版：自动检测环境、安装依赖、创建启动入口
set -euo pipefail

INSTALL_DIR="${HOME}/.local/share/pdf-to-word"
DESKTOP_DIR="${HOME}/.local/share/applications"
BIN_DIR="${HOME}/.local/bin"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
VENV_DIR="$INSTALL_DIR/venv"
LAUNCHER="$BIN_DIR/pdf-to-word"
DESKTOP_FILE="$DESKTOP_DIR/pdf-to-word.desktop"

echo "========================================"
echo " PDF 工具箱 — 麒麟 / Linux 安装"
echo "========================================"

install_apt_deps() {
    echo "检测到 apt 包管理器，安装系统依赖..."
    sudo apt-get update
    sudo apt-get install -y python3 python3-pip python3-venv python3-tk
}

install_yum_deps() {
    echo "检测到 yum/dnf 包管理器，安装系统依赖..."
    if command -v dnf >/dev/null 2>&1; then
        sudo dnf install -y python3 python3-pip python3-tkinter
    else
        sudo yum install -y python3 python3-pip python3-tkinter
    fi
}

if command -v apt-get >/dev/null 2>&1; then
    install_apt_deps
elif command -v dnf >/dev/null 2>&1 || command -v yum >/dev/null 2>&1; then
    install_yum_deps
else
    echo "[警告] 未识别包管理器，请手动确保已安装：python3、python3-pip、python3-tk"
fi

if ! python3 -c "import tkinter" 2>/dev/null; then
    echo "[错误] tkinter 不可用，图形界面无法启动。"
    echo "请安装：sudo apt install python3-tk  或  sudo dnf install python3-tkinter"
    exit 1
fi

echo ""
echo "安装程序到: $INSTALL_DIR"
mkdir -p "$INSTALL_DIR/app" "$BIN_DIR" "$DESKTOP_DIR"
rm -rf "$INSTALL_DIR/app"
if command -v rsync >/dev/null 2>&1; then
    rsync -a \
        --exclude ".venv" \
        --exclude ".venv-build" \
        --exclude ".venv-build-linux" \
        --exclude "dist" \
        --exclude "build" \
        --exclude "installer/output" \
        "$PROJECT_ROOT/" "$INSTALL_DIR/app/"
else
    cp -r "$PROJECT_ROOT/." "$INSTALL_DIR/app/"
    rm -rf \
        "$INSTALL_DIR/app/.venv" \
        "$INSTALL_DIR/app/.venv-build" \
        "$INSTALL_DIR/app/.venv-build-linux" \
        "$INSTALL_DIR/app/dist" \
        "$INSTALL_DIR/app/build" \
        "$INSTALL_DIR/app/installer/output"
fi

if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip
python -m pip install -r "$INSTALL_DIR/app/requirements.txt"

cat > "$LAUNCHER" <<EOF
#!/usr/bin/env bash
source "$VENV_DIR/bin/activate"
exec python "$INSTALL_DIR/app/pdf_to_word_gui.py" "\$@"
EOF
chmod +x "$LAUNCHER"

cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Name=PDF 工具箱
Comment=PDF 转 Word、拼接、拆分
Exec=$LAUNCHER
Icon=application-pdf
Terminal=false
Type=Application
Categories=Office;Utility;
EOF
chmod +x "$DESKTOP_FILE"

echo ""
echo "========================================"
echo " 安装完成"
echo "========================================"
echo "命令行启动: pdf-to-word"
echo "桌面入口:   应用菜单中搜索「PDF 工具箱」"
echo ""
echo "若菜单未显示，可执行: update-desktop-database ~/.local/share/applications 2>/dev/null || true"
