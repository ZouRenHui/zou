#!/usr/bin/env bash
# PDF 工具箱启动脚本（麒麟 / Linux 免安装版）

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR" || exit 1

# shellcheck disable=SC1091
source "$DIR/arch-check.sh" 2>/dev/null || {
    arch_check() { return 0; }
    print_arch_mismatch_help() { true; }
}

chmod +x "./PdfToWord" "./run.sh" "./check-kylin.sh" 2>/dev/null || true

if [ ! -f "./PdfToWord" ]; then
    echo "[错误] 找不到 PdfToWord 可执行文件。"
    echo "请确认已完整解压，且 _internal 目录与本文件在同一文件夹内。"
    exit 1
fi

if [ ! -d "./_internal" ]; then
    echo "[错误] 找不到 _internal 依赖目录。"
    echo "请勿只复制 PdfToWord 文件，必须保留整个 PdfToWord 文件夹。"
    exit 1
fi

if ! check_arch_match; then
    bin_arch="$(detect_binary_arch 2>/dev/null || echo 未知)"
    print_arch_mismatch_help "$(uname -m)" "$bin_arch"
    exit 1
fi

# 不用 set -e，避免二进制格式错误时输出混乱
./PdfToWord "$@"
code=$?

if [ "$code" -ne 0 ]; then
    echo ""
    if [ "$code" -eq 126 ] || [ "$code" -eq 127 ]; then
        print_arch_mismatch_help "$(uname -m)" "$(detect_binary_arch 2>/dev/null || echo 未知)"
    else
        echo "程序未能正常启动 (退出码: $code)"
        echo "请执行: ./check-kylin.sh"
        echo "或安装运行库: sudo apt install libgl1 libglib2.0-0 libxkbcommon0"
    fi
    exit "$code"
fi
