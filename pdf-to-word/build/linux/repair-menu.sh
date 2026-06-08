#!/usr/bin/env bash
# 一键修复：开始菜单 / 桌面快捷方式 / 启动脚本（全程图形界面，无需命令行）
set -u

APP_NAME="PDF 工具箱"
APP_ID="pdf-toolbox"
REPAIR_ID="pdf-toolbox-repair"
INSTALL_ROOT="${PDF_TOOLBOX_INSTALL:-$HOME/.local/share/pdf-to-word}"
VENV_DIR="$INSTALL_ROOT/venv"
LAUNCHER="$INSTALL_ROOT/run-python.sh"
MENU_DIR="${HOME}/.local/share/applications"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck disable=SC1091
source "$SCRIPT_DIR/gui-dialog.sh" 2>/dev/null || true
# shellcheck disable=SC1091
source "$SCRIPT_DIR/python-launcher.sh" 2>/dev/null || true
# shellcheck disable=SC1091
source "$SCRIPT_DIR/desktop-shortcut.sh" 2>/dev/null || true

POST_INSTALL=false
if [ "${1:-}" = "--post-install" ]; then
    POST_INSTALL=true
fi

ensure_helpers_in_install_root() {
    local f
    mkdir -p "$INSTALL_ROOT"
    for f in python-launcher.sh desktop-shortcut.sh gui-dialog.sh repair-menu.sh; do
        if [ -f "$SCRIPT_DIR/$f" ] && [ ! -f "$INSTALL_ROOT/$f" ]; then
            cp "$SCRIPT_DIR/$f" "$INSTALL_ROOT/"
            chmod +x "$INSTALL_ROOT/$f" 2>/dev/null || true
        fi
    done
    if [ -f "$SCRIPT_DIR/repair-menu.sh" ]; then
        cp "$SCRIPT_DIR/repair-menu.sh" "$INSTALL_ROOT/"
        chmod +x "$INSTALL_ROOT/repair-menu.sh" 2>/dev/null || true
    fi
}

create_launch_shortcut() {
    local exec_line menu_file
    if ! type desktop_exec_line >/dev/null 2>&1; then
        exec_line="Exec=/bin/bash \"${LAUNCHER}\""
    else
        exec_line="$(desktop_exec_line "$LAUNCHER")"
    fi

    menu_file="${MENU_DIR}/${APP_ID}.desktop"
    cat > "$menu_file" <<EOF
[Desktop Entry]
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
EOF

    if type install_menu_and_desktop_shortcuts >/dev/null 2>&1; then
        install_menu_and_desktop_shortcuts "$menu_file" "$APP_ID" "$APP_NAME" || true
    else
        mkdir -p "$MENU_DIR"
        trust_desktop_file "$menu_file" 2>/dev/null || chmod +x "$menu_file"
    fi
}

create_repair_shortcut() {
    local repair_script="$INSTALL_ROOT/repair-menu.sh"
    local exec_line menu_file

    if [ ! -x "$repair_script" ]; then
        cp "$SCRIPT_DIR/repair-menu.sh" "$repair_script" 2>/dev/null || true
        chmod +x "$repair_script" 2>/dev/null || true
    fi

    exec_line="Exec=/bin/bash \"${repair_script}\""
    menu_file="${MENU_DIR}/${REPAIR_ID}.desktop"
    cat > "$menu_file" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=修复 PDF 工具箱
Name[zh_CN]=修复 PDF 工具箱
Comment=程序打不开时，双击这里自动修复
Comment[zh_CN]=程序打不开时，双击这里自动修复
${exec_line}
Path=${INSTALL_ROOT}
Icon=system-software-update
Terminal=false
Categories=Utility;
StartupNotify=true
EOF

    if type install_menu_and_desktop_shortcuts >/dev/null 2>&1; then
        install_menu_and_desktop_shortcuts "$menu_file" "$REPAIR_ID" "修复 PDF 工具箱" || true
    else
        mkdir -p "$MENU_DIR"
        trust_desktop_file "$menu_file" 2>/dev/null || chmod +x "$menu_file"
    fi
}

do_repair() {
    rm -f "${MENU_DIR}/pdf-to-word.desktop"

    if [ ! -d "$INSTALL_ROOT/app" ]; then
        gui_error "尚未安装 PDF 工具箱。\n\n请先双击运行：\nPdfToWord-Kylin-aarch64.run\n\n完成安装后再点「修复」。"
        exit 1
    fi

    if ! type write_python_launcher >/dev/null 2>&1; then
        gui_error "修复组件不完整。\n\n请重新下载安装包，双击运行 .run 文件重新安装。"
        exit 1
    fi

    ensure_helpers_in_install_root
    write_python_launcher "$INSTALL_ROOT" "$VENV_DIR" "$LAUNCHER" "$APP_NAME"
    create_launch_shortcut
    create_repair_shortcut

    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database "$MENU_DIR" 2>/dev/null || true
    fi
}

main() {
    if ! $POST_INSTALL && type gui_info >/dev/null 2>&1; then
        gui_info "即将自动修复 PDF 工具箱。\n\n请点击「确定」，等待片刻即可。"
    fi

    do_repair

    if $POST_INSTALL; then
        gui_info "安装完成！\n\n请使用桌面上的图标：\n\n• PDF 工具箱 — 打开程序\n• 修复 PDF 工具箱 — 若打不开请点这个\n\n开始菜单里也可搜索「PDF 工具箱」。"
        if type gui_question >/dev/null 2>&1 && gui_question "是否现在打开 PDF 工具箱？"; then
            /bin/bash "$LAUNCHER" &
        fi
        exit 0
    fi

    gui_info "修复完成！\n\n请双击桌面上的「PDF 工具箱」打开程序。\n\n若仍打不开，请再次双击「修复 PDF 工具箱」，或联系安装人员。"
    if type gui_question >/dev/null 2>&1 && gui_question "是否现在尝试打开 PDF 工具箱？"; then
        /bin/bash "$LAUNCHER" &
    fi
}

main "$@"
