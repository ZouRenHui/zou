#!/usr/bin/env bash
# 生成 PDF 工具箱 Python 模式启动脚本（菜单/桌面双击时显示错误，不写日志到黑洞）

write_python_launcher() {
    local install_root="$1"
    local venv_dir="$2"
    local launcher="$3"
    local app_name="${4:-PDF 工具箱}"

    mkdir -p "$install_root"
    cat > "$launcher" <<EOF
#!/usr/bin/env bash
INSTALL_ROOT="${install_root}"
VENV_DIR="${venv_dir}"
APP_PY="\${INSTALL_ROOT}/app/pdf_to_word_gui.py"
LOG="\${INSTALL_ROOT}/launch.log"
APP_NAME="${app_name}"

show_error() {
    local msg="\$1"
    {
        echo "=== \$(date '+%Y-%m-%d %H:%M:%S') ERROR ==="
        echo "\$msg"
    } >> "\$LOG" 2>&1
    if command -v zenity >/dev/null 2>&1; then
        zenity --error --title="\$APP_NAME" --text="\$msg" --width=500 2>/dev/null || true
    elif command -v kdialog >/dev/null 2>&1; then
        kdialog --error "\$msg" 2>/dev/null || true
    fi
}

{
    echo "=== Launch \$(date '+%Y-%m-%d %H:%M:%S') ==="
    echo "DISPLAY=\${DISPLAY:-unset} HOME=\$HOME"
    echo "PWD=\$(pwd)"
} >> "\$LOG" 2>&1

export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:\${PATH:-}"
export LANG="\${LANG:-zh_CN.UTF-8}"
export LC_ALL="\${LC_ALL:-zh_CN.UTF-8}"
if [ -z "\${DISPLAY:-}" ]; then
    export DISPLAY=:0
fi

cd "\$INSTALL_ROOT" 2>/dev/null || true

if [ ! -f "\$APP_PY" ]; then
    show_error "未找到程序文件：\n\$APP_PY\n\n请重新运行 PdfToWord-Kylin-aarch64.run 安装。"
    exit 1
fi

launch_with_python() {
    local py="\$1"
    echo "Starting: \$py \$APP_PY" >> "\$LOG"
    exec "\$py" "\$APP_PY" "\$@"
}

if [ -f "\$VENV_DIR/bin/activate" ]; then
    # shellcheck disable=SC1091
    source "\$VENV_DIR/bin/activate"
    if python -c "import tkinter" 2>/dev/null; then
        launch_with_python python
    fi
    echo "venv python: tkinter unavailable, fallback to system python3" >> "\$LOG"
fi

if command -v python3 >/dev/null 2>&1 && python3 -c "import tkinter" 2>/dev/null; then
    launch_with_python python3
fi

show_error "无法启动图形界面（tkinter 不可用）。\n\n请在终端执行：\n  sudo apt-get install -y python3-tk\n  ~/.local/share/pdf-to-word/run-python.sh\n\n详细日志：\n\$LOG"
exit 1
EOF
    chmod +x "$launcher"
}

# 桌面 / 菜单 .desktop 的 Exec（必须用 bash 显式调用，麒麟 UKUI 才可靠）
desktop_exec_line() {
    local launcher="$1"
    printf 'Exec=/bin/bash "%s"' "$launcher"
}
