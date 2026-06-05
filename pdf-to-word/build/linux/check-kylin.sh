#!/usr/bin/env bash
# 麒麟 / Linux 运行环境检测
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR" || exit 1

# shellcheck disable=SC1091
source "$DIR/arch-check.sh" 2>/dev/null || true

echo "========================================"
echo " PDF 工具箱 — 环境检测"
echo "========================================"
echo "程序目录: $DIR"
echo ""

ok=true

check() {
    local name="$1"
    local result="$2"
    if [ "$result" = "ok" ]; then
        echo "[OK]   $name"
    else
        echo "[FAIL] $name — $result"
        ok=false
    fi
}

host_arch="$(uname -m)"
check "系统架构" "$host_arch ($(normalize_arch "$host_arch" 2>/dev/null || echo "$host_arch"))"

if [ -f "./PdfToWord" ]; then
    check "主程序 PdfToWord" "ok"
    if command -v file >/dev/null 2>&1; then
        bin_desc="$(file -b ./PdfToWord)"
        check "程序文件类型" "$bin_desc"
    fi
    if declare -f check_arch_match >/dev/null && ! check_arch_match 2>/dev/null; then
        bin_arch="$(detect_binary_arch 2>/dev/null || echo 未知)"
        check "架构匹配" "不匹配！系统 $(normalize_arch "$host_arch") vs 程序 $bin_arch"
        echo ""
        print_arch_mismatch_help "$host_arch" "$bin_arch"
        exit 1
    else
        check "架构匹配" "ok"
    fi
    if [ ! -x "./PdfToWord" ]; then
        chmod +x "./PdfToWord" 2>/dev/null || true
        check "执行权限" "$([ -x ./PdfToWord ] && echo ok || echo 请执行 chmod +x PdfToWord)"
    fi
else
    check "主程序 PdfToWord" "文件不存在"
fi

if [ -d "./_internal" ]; then
    check "依赖目录 _internal" "ok"
else
    check "依赖目录 _internal" "缺失，请勿单独移动 PdfToWord 可执行文件"
fi

if command -v ldd >/dev/null 2>&1 && [ -f "./PdfToWord" ]; then
    missing="$(ldd ./PdfToWord 2>/dev/null | grep 'not found' || true)"
    if [ -z "$missing" ]; then
        check "动态库链接" "ok"
    else
        check "动态库链接" "缺少: $(echo "$missing" | tr '\n' ' ')"
    fi
fi

if [ -n "${DISPLAY:-}" ] || [ -n "${WAYLAND_DISPLAY:-}" ]; then
    check "图形环境" "ok (${DISPLAY:-$WAYLAND_DISPLAY})"
else
    check "图形环境" "未检测到 DISPLAY，可能无法打开窗口"
fi

echo ""
if $ok; then
    echo "环境检测通过，可执行: ./run.sh"
    exit 0
fi

echo "环境检测未完全通过。可尝试："
echo "  sudo apt install libgl1 libglib2.0-0 libxkbcommon0 libxcb-xinerama0"
exit 1
