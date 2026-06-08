#!/usr/bin/env bash
# 修复开始菜单 / 桌面快捷方式（已安装用户可在终端运行，无需重装 .run）
set -euo pipefail

APP_NAME="PDF 工具箱"
APP_ID="pdf-toolbox"
INSTALL_ROOT="${PDF_TOOLBOX_INSTALL:-$HOME/.local/share/pdf-to-word}"
VENV_DIR="$INSTALL_ROOT/venv"
LAUNCHER="$INSTALL_ROOT/run-python.sh"
MENU_DIR="${HOME}/.local/share/applications"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck disable=SC1091
source "$SCRIPT_DIR/python-launcher.sh" 2>/dev/null || {
    echo "[错误] 未找到 python-launcher.sh"
    exit 1
}
# shellcheck disable=SC1091
source "$SCRIPT_DIR/desktop-shortcut.sh" 2>/dev/null || true

if [ ! -d "$INSTALL_ROOT/app" ]; then
    echo "[错误] 未找到已安装程序: $INSTALL_ROOT/app"
    echo "请先运行 PdfToWord-Kylin-aarch64.run 完成安装。"
    exit 1
fi

write_python_launcher "$INSTALL_ROOT" "$VENV_DIR" "$LAUNCHER" "$APP_NAME"
echo "[OK] 启动脚本: $LAUNCHER"

exec_line="$(desktop_exec_line "$LAUNCHER")"
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

rm -f "${MENU_DIR}/pdf-to-word.desktop"
MENU_FILE="${MENU_DIR}/${APP_ID}.desktop"
printf '%s' "$DESKTOP_CONTENT" > "$MENU_FILE"

if type install_menu_and_desktop_shortcuts >/dev/null 2>&1; then
    install_menu_and_desktop_shortcuts "$MENU_FILE" "$APP_ID" "$APP_NAME" || true
fi

echo ""
echo "修复完成。请从开始菜单重新打开「${APP_NAME}」。"
echo "若仍无反应，终端测试: $LAUNCHER"
echo "日志文件: $INSTALL_ROOT/launch.log"
