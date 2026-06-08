#!/usr/bin/env bash
# 图形对话框（zenity / kdialog），供安装与修复脚本使用

APP_NAME="${APP_NAME:-PDF 工具箱}"

gui_info() {
    if command -v zenity >/dev/null 2>&1; then
        zenity --info --title="$APP_NAME" --text="$1" --width=480 2>/dev/null && return 0
    fi
    if command -v kdialog >/dev/null 2>&1; then
        kdialog --msgbox "$1" 2>/dev/null && return 0
    fi
    echo "$1"
    return 0
}

gui_error() {
    if command -v zenity >/dev/null 2>&1; then
        zenity --error --title="$APP_NAME" --text="$1" --width=480 2>/dev/null && return 0
    fi
    if command -v kdialog >/dev/null 2>&1; then
        kdialog --error "$1" 2>/dev/null && return 0
    fi
    echo "[错误] $1" >&2
    return 1
}

gui_question() {
    if command -v zenity >/dev/null 2>&1; then
        zenity --question --title="$APP_NAME" --text="$1" --width=480 2>/dev/null
        return $?
    fi
    if command -v kdialog >/dev/null 2>&1; then
        kdialog --yesno "$1" 2>/dev/null
        return $?
    fi
    echo "$1"
    read -r -p "是否继续？(y/n): " ans
    [[ "$ans" =~ ^[Yy] ]]
}

gui_progress_run() {
    local title="$1"
    local text="$2"
    shift 2
    if command -v zenity >/dev/null 2>&1; then
        (
            echo "5"; echo "# $text"
            "$@"
            echo "100"; echo "# 完成"
        ) | zenity --progress --title="$title" --text="$text" --percentage=0 --auto-close --width=420 2>/dev/null \
            && return 0
    fi
    "$@"
}
