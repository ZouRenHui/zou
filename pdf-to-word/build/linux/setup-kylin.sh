#!/usr/bin/env bash
# PDF 工具箱 — 麒麟一键安装（图形界面双击可用）
# 与 PdfToWord-Kylin-*.tar.gz 放在同一文件夹，双击本文件即可完成解压与创建快捷方式
set -euo pipefail

APP_NAME="PDF 工具箱"
INSTALL_BASE="${PDF_TOOLBOX_HOME:-$HOME/.local/share}"
INSTALL_DIR="$INSTALL_BASE/PdfToWord"
SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}" 2>/dev/null || realpath "${BASH_SOURCE[0]}" 2>/dev/null || echo "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"

chmod +x "$SCRIPT_PATH" 2>/dev/null || true

gui_info() {
    if command -v zenity >/dev/null 2>&1; then
        zenity --info --title="$APP_NAME" --text="$1" --width=420 2>/dev/null || echo "$1"
    elif command -v kdialog >/dev/null 2>&1; then
        kdialog --msgbox "$1" 2>/dev/null || echo "$1"
    else
        echo "$1"
        [ -t 0 ] || read -r -p "按回车键关闭..." _ </dev/tty 2>/dev/null || true
    fi
}

gui_error() {
    if command -v zenity >/dev/null 2>&1; then
        zenity --error --title="$APP_NAME" --text="$1" --width=420 2>/dev/null || echo "[错误] $1" >&2
    elif command -v kdialog >/dev/null 2>&1; then
        kdialog --error "$1" 2>/dev/null || echo "[错误] $1" >&2
    else
        echo "[错误] $1" >&2
        [ -t 0 ] || read -r -p "按回车键关闭..." _ </dev/tty 2>/dev/null || true
    fi
}

gui_question() {
    if command -v zenity >/dev/null 2>&1; then
        zenity --question --title="$APP_NAME" --text="$1" --width=420 2>/dev/null
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

find_tarball() {
    local candidate
    for candidate in "$SCRIPT_DIR"/PdfToWord-Kylin-*.tar.gz; do
        if [ -f "$candidate" ]; then
            echo "$candidate"
            return 0
        fi
    done
    return 1
}

install_from_tarball() {
    local tar_file="$1"
    mkdir -p "$INSTALL_BASE"
    if [ -d "$INSTALL_DIR" ]; then
        if ! gui_question "已存在安装目录：\n$INSTALL_DIR\n\n是否覆盖并重新安装？"; then
            return 0
        fi
        rm -rf "$INSTALL_DIR"
    fi
    echo "正在解压: $(basename "$tar_file")"
    tar -xzf "$tar_file" -C "$INSTALL_BASE"
    if [ ! -f "$INSTALL_DIR/run.sh" ]; then
        gui_error "解压失败：未找到 $INSTALL_DIR/run.sh\n请确认 tar.gz 包是否完整。"
        exit 1
    fi
}

create_shortcuts() {
    chmod +x "$INSTALL_DIR/run.sh" "$INSTALL_DIR/PdfToWord" \
        "$INSTALL_DIR/install-shortcut.sh" 2>/dev/null || true
    if [ -x "$INSTALL_DIR/install-shortcut.sh" ]; then
        (cd "$INSTALL_DIR" && ./install-shortcut.sh)
    else
        gui_error "未找到 install-shortcut.sh"
        exit 1
    fi
}

launch_app() {
    if gui_question "安装完成！\n\n是否立即启动 $APP_NAME？"; then
        exec "$INSTALL_DIR/run.sh"
    fi
}

main() {
    local tar_file=""
    tar_file="$(find_tarball)" || tar_file=""

    if [ -f "$INSTALL_DIR/run.sh" ] && [ -z "$tar_file" ]; then
        if gui_question "检测到已安装 $APP_NAME。\n\n是否重新创建桌面快捷方式？"; then
            create_shortcuts
            gui_info "快捷方式已更新。\n\n请从桌面或应用菜单打开「$APP_NAME」。"
        fi
        if gui_question "是否立即启动 $APP_NAME？"; then
            exec "$INSTALL_DIR/run.sh"
        fi
        exit 0
    fi

    if ! tar_file="$(find_tarball)"; then
        gui_error "未找到安装包 PdfToWord-Kylin-*.tar.gz\n\n请将本脚本与 tar.gz 放在同一文件夹后再双击运行。"
        exit 1
    fi

    install_from_tarball "$tar_file"
    create_shortcuts
    gui_info "安装成功！\n\n安装位置：\n$INSTALL_DIR\n\n已创建桌面与应用菜单快捷方式「$APP_NAME」。"
    launch_app
}

main "$@"
