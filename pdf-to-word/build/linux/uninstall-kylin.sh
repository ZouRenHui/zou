#!/usr/bin/env bash
# 卸载 PDF 工具箱（麒麟 / Linux）
set -euo pipefail

APP_NAME="PDF 工具箱"
PORTABLE_DIR="${HOME}/.local/share/PdfToWord"
PYTHON_DIR="${HOME}/.local/share/pdf-to-word"
MENU_DIR="${HOME}/.local/share/applications"
BIN_LAUNCHER="${HOME}/.local/bin/pdf-to-word"
DESKTOP_NAMES=("Desktop" "桌面")

gui_info() {
    if command -v zenity >/dev/null 2>&1; then
        zenity --info --title="$APP_NAME" --text="$1" --width=420 2>/dev/null || echo "$1"
    else
        echo "$1"
    fi
}

gui_question() {
    if command -v zenity >/dev/null 2>&1; then
        zenity --question --title="$APP_NAME" --text="$1" --width=420 2>/dev/null
        return $?
    else
        read -r -p "$1 (y/n): " ans
        [[ "$ans" =~ ^[Yy] ]]
    fi
}

removed=()

remove_path() {
    local path="$1"
    if [ -e "$path" ]; then
        rm -rf "$path"
        removed+=("$path")
        echo "[已删除] $path"
    fi
}

echo "========================================"
echo " 卸载 ${APP_NAME}"
echo "========================================"
echo ""
echo "将删除以下内容（若存在）："
echo "  - $PORTABLE_DIR          (旧版 PyInstaller 安装)"
echo "  - $PYTHON_DIR            (Python 模式安装)"
echo "  - 桌面 / 应用菜单快捷方式"
echo "  - $BIN_LAUNCHER"
echo ""

if ! gui_question "确定要卸载 ${APP_NAME} 吗？"; then
    echo "已取消。"
    exit 0
fi

remove_path "$PORTABLE_DIR"
remove_path "$PYTHON_DIR"
remove_path "$BIN_LAUNCHER"

for id in pdf-toolbox pdf-to-word; do
    remove_path "$MENU_DIR/${id}.desktop"
    for name in "${DESKTOP_NAMES[@]}"; do
        remove_path "${HOME}/${name}/${id}.desktop"
    done
done

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$MENU_DIR" 2>/dev/null || true
fi

echo ""
if [ ${#removed[@]} -eq 0 ]; then
    gui_info "未找到已安装的文件，可能已卸载。"
else
    gui_info "卸载完成！\n\n已删除 ${#removed[@]} 项。\n\n可安装新版 PdfToWord-Kylin-aarch64.run。"
fi
