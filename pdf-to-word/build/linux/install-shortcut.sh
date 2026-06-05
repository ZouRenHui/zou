#!/usr/bin/env bash
# 安装 PDF 工具箱桌面快捷方式（应用菜单 + 桌面）
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_NAME="PDF 工具箱"
APP_ID="pdf-toolbox"
RUN_SCRIPT="$APP_DIR/run.sh"
MENU_DIR="${HOME}/.local/share/applications"
DESKTOP_NAMES=("Desktop" "桌面")

if [ ! -f "$RUN_SCRIPT" ]; then
    echo "[错误] 找不到 $RUN_SCRIPT"
    echo "请在 PdfToWord 文件夹内执行本脚本。"
    exit 1
fi

chmod +x "$RUN_SCRIPT" "$APP_DIR/PdfToWord" 2>/dev/null || true

mkdir -p "$MENU_DIR"

DESKTOP_CONTENT="[Desktop Entry]
Version=1.0
Type=Application
Name=${APP_NAME}
Name[zh_CN]=${APP_NAME}
Comment=PDF 转 Word、拼接、拆分
Comment[zh_CN]=PDF 转 Word、拼接、拆分
Exec=${RUN_SCRIPT}
Path=${APP_DIR}
Icon=application-pdf
Terminal=false
Categories=Office;Utility;
StartupNotify=true
"

MENU_FILE="${MENU_DIR}/${APP_ID}.desktop"
printf '%s' "$DESKTOP_CONTENT" > "$MENU_FILE"
chmod +x "$MENU_FILE"

desktop_linked=false
for name in "${DESKTOP_NAMES[@]}"; do
    desk="${HOME}/${name}"
    if [ -d "$desk" ]; then
        cp "$MENU_FILE" "${desk}/${APP_ID}.desktop"
        chmod +x "${desk}/${APP_ID}.desktop"
        echo "[OK] 桌面快捷方式: ${desk}/${APP_ID}.desktop"
        desktop_linked=true
        break
    fi
done

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$MENU_DIR" 2>/dev/null || true
fi

echo ""
echo "========================================"
echo " 快捷方式已创建"
echo "========================================"
echo "应用菜单: 搜索「${APP_NAME}」"
if $desktop_linked; then
    echo "桌面:     双击「${APP_NAME}」图标"
else
    echo "桌面:     未找到 Desktop/桌面 目录，仅已添加到应用菜单"
fi
echo ""
echo "启动命令: ${RUN_SCRIPT}"
