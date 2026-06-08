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
# shellcheck disable=SC1091
source "$APP_DIR/install-system-deps.sh" 2>/dev/null || true
# shellcheck disable=SC1091
source "$APP_DIR/desktop-shortcut.sh" 2>/dev/null || true
# shellcheck disable=SC1091
source "$APP_DIR/python-launcher.sh" 2>/dev/null || true

gui_info() {
    if command -v zenity >/dev/null 2>&1; then
        zenity --info --title="$APP_NAME" --text="$1" --width=460 2>/dev/null || echo "$1"
    else
        echo "$1"
    fi
}

gui_error() {
    if command -v zenity >/dev/null 2>&1; then
        zenity --error --title="$APP_NAME" --text="$1" --width=460 2>/dev/null || echo "[错误] $1" >&2
    else
        echo "[错误] $1" >&2
    fi
}

gui_question() {
    if command -v zenity >/dev/null 2>&1; then
        zenity --question --title="$APP_NAME" --text="$1" --width=460 2>/dev/null
        return $?
    elif command -v kdialog >/dev/null 2>&1; then
        kdialog --yesno "$1" 2>/dev/null
        return $?
    else
        echo "$1"
        read -r -p "是否继续？(y/n): " ans
        [[ "$ans" =~ ^[Yy] ]]
    fi
}

if [ ! -d "$SOURCE_DIR" ] && ! $SHORTCUT_ONLY; then
    gui_error "未找到 app_source 源码目录。\n请使用最新版 PdfToWord-Kylin-aarch64.run 安装包。"
    exit 1
fi

ensure_tkinter_or_exit() {
    if type ensure_tkinter >/dev/null 2>&1; then
        if ensure_tkinter gui_question; then
            return 0
        fi
        if type tkinter_failure_message >/dev/null 2>&1; then
            gui_error "$(tkinter_failure_message)"
        else
            gui_error "缺少 python3-tk，图形界面无法启动。\n\n请在终端执行：\n  sudo apt-get install -y python3 python3-tk\n\n安装完成后重新双击安装包。"
        fi
        exit 1
    fi

    if ! python3 -c "import tkinter" 2>/dev/null; then
        gui_error "缺少 python3-tk，图形界面无法启动。\n\n请在终端执行：\n  sudo apt-get install -y python3 python3-tk\n\n安装完成后重新双击安装包。"
        exit 1
    fi
}

setup_app() {
    echo "安装 Python 版到: $INSTALL_ROOT"
    mkdir -p "$INSTALL_ROOT/app"
    rm -rf "$INSTALL_ROOT/app"
    cp -a "$SOURCE_DIR/." "$INSTALL_ROOT/app/"

    # tkinter 是系统包，venv 必须保留 system-site-packages 才能 import tkinter
    if [ ! -d "$VENV_DIR" ]; then
        python3 -m venv --system-site-packages "$VENV_DIR"
    elif ! grep -q 'include-system-site-packages = true' "$VENV_DIR/pyvenv.cfg" 2>/dev/null; then
        echo "重建虚拟环境（启用 system-site-packages 以支持 tkinter）..."
        rm -rf "$VENV_DIR"
        python3 -m venv --system-site-packages "$VENV_DIR"
    fi

    # shellcheck disable=SC1091
    source "$VENV_DIR/bin/activate"

    if ! check_tkinter python; then
        echo "[警告] 虚拟环境中 tkinter 不可用，尝试修复..."
        if type reinstall_apt_tk_packages >/dev/null 2>&1; then
            reinstall_apt_tk_packages || true
        fi
        if ! check_tkinter python; then
            local msg
            msg="$(type tkinter_failure_message >/dev/null 2>&1 && tkinter_failure_message || echo "虚拟环境中 tkinter 不可用")"
            gui_error "$msg"
            exit 1
        fi
    fi

    python -m pip install --upgrade pip -q
    if command -v zenity >/dev/null 2>&1; then
        (
            echo "10"; echo "# 正在安装依赖..."
            python -m pip install -r "$INSTALL_ROOT/app/requirements.txt" -q
            echo "100"; echo "# 完成"
        ) | zenity --progress --title="$APP_NAME" --text="正在配置运行环境，请稍候..." --percentage=0 --auto-close 2>/dev/null \
            || python -m pip install -r "$INSTALL_ROOT/app/requirements.txt" -q
    else
        python -m pip install -r "$INSTALL_ROOT/app/requirements.txt" -q
    fi

    if type write_python_launcher >/dev/null 2>&1; then
        write_python_launcher "$INSTALL_ROOT" "$VENV_DIR" "$LAUNCHER" "$APP_NAME"
    else
        cat > "$LAUNCHER" <<EOF
#!/usr/bin/env bash
source "$VENV_DIR/bin/activate"
exec python "$INSTALL_ROOT/app/pdf_to_word_gui.py" "\$@"
EOF
        chmod +x "$LAUNCHER"
    fi
    echo "[OK] 启动脚本: $LAUNCHER"

    for helper in python-launcher.sh desktop-shortcut.sh repair-menu.sh gui-dialog.sh; do
        if [ -f "$APP_DIR/$helper" ]; then
            cp "$APP_DIR/$helper" "$INSTALL_ROOT/"
            chmod +x "$INSTALL_ROOT/$helper" 2>/dev/null || true
        fi
    done
}

create_shortcuts() {
    local exec_line="Exec=${LAUNCHER}"
    if type desktop_exec_line >/dev/null 2>&1; then
        exec_line="$(desktop_exec_line "$LAUNCHER")"
    fi

    # 移除旧版菜单项（可能指向 PyInstaller 二进制，点击无反应）
    rm -f "${MENU_DIR}/pdf-to-word.desktop"

    DESKTOP_CONTENT="[Desktop Entry]
Version=1.0
Type=Application
Name=${APP_NAME}
Name[zh_CN]=${APP_NAME}
Comment=PDF 转 Word、拼接、拆分
Comment[zh_CN]=PDF 转 Word、拼接、拆分
${exec_line}
Path=${INSTALL_ROOT}
Icon=application-pdf
Terminal=false
Categories=Office;Utility;
StartupNotify=true
"

    MENU_FILE="${MENU_DIR}/${APP_ID}.desktop"
    printf '%s' "$DESKTOP_CONTENT" > "$MENU_FILE"

    if type install_menu_and_desktop_shortcuts >/dev/null 2>&1; then
        install_menu_and_desktop_shortcuts "$MENU_FILE" "$APP_ID" "$APP_NAME" || true
    else
        mkdir -p "$MENU_DIR"
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
    fi
}

if ! $SHORTCUT_ONLY; then
    ensure_tkinter_or_exit
    setup_app
else
    # 仅重建快捷方式时，同步修复启动脚本（解决菜单点击无反应）
    for helper in python-launcher.sh desktop-shortcut.sh gui-dialog.sh repair-menu.sh; do
        if [ -f "$APP_DIR/$helper" ]; then
            cp "$APP_DIR/$helper" "$INSTALL_ROOT/"
            chmod +x "$INSTALL_ROOT/$helper" 2>/dev/null || true
        fi
    done
    if [ -d "$VENV_DIR" ] && type write_python_launcher >/dev/null 2>&1; then
        write_python_launcher "$INSTALL_ROOT" "$VENV_DIR" "$LAUNCHER" "$APP_NAME"
        echo "[OK] 已更新启动脚本: $LAUNCHER"
    fi
fi

if [ ! -x "$LAUNCHER" ]; then
    gui_error "安装未完成：未找到 $LAUNCHER"
    exit 1
fi

create_shortcuts

if [ -x "$INSTALL_ROOT/repair-menu.sh" ]; then
    if $SHORTCUT_ONLY; then
        bash "$INSTALL_ROOT/repair-menu.sh" || true
    else
        bash "$INSTALL_ROOT/repair-menu.sh" --post-install || true
    fi
elif [ -t 1 ]; then
    echo ""
    echo "========================================"
    echo " 麒麟 Python 模式安装完成"
    echo "========================================"
    echo "启动: $LAUNCHER"
    echo "桌面: $(find_desktop_dirs 2>/dev/null | head -1 || echo '~/桌面')/${APP_ID}.desktop"
    echo "菜单: 搜索「${APP_NAME}」"
else
    gui_info "安装成功！\n\n请双击桌面上的「PDF 工具箱」打开。\n\n若打不开，请双击「修复 PDF 工具箱」。"
fi
