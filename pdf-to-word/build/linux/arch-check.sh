#!/usr/bin/env bash
# 检测系统架构与 PdfToWord 二进制是否匹配

normalize_arch() {
    case "$1" in
        x86_64|amd64|i686) echo "x86_64" ;;
        aarch64|arm64) echo "aarch64" ;;
        armv7l|armv8l) echo "arm" ;;
        loongarch64) echo "loongarch64" ;;
        *) echo "$1" ;;
    esac
}

detect_binary_arch() {
    local bin="./PdfToWord"
    [ -f "$bin" ] || return 1

    if command -v file >/dev/null 2>&1; then
        local info
        info="$(file -b "$bin")"
        if echo "$info" | grep -qiE 'x86-64|x86_64|80386'; then
            echo "x86_64"
            return 0
        fi
        if echo "$info" | grep -qi 'aarch64'; then
            echo "aarch64"
            return 0
        fi
        if echo "$info" | grep -qiE 'ARM|arm'; then
            echo "arm"
            return 0
        fi
        if echo "$info" | grep -qi 'loongarch'; then
            echo "loongarch64"
            return 0
        fi
        echo "$info"
        return 0
    fi
    return 1
}

check_arch_match() {
    local host bin host_n bin_n
    host="$(uname -m)"
    host_n="$(normalize_arch "$host")"
    bin="$(detect_binary_arch)" || return 0
    bin_n="$(normalize_arch "$bin")"

    if [ "$host_n" != "$bin_n" ]; then
        return 1
    fi
    return 0
}

print_arch_mismatch_help() {
    local host="${1:-$(uname -m)}"
    echo ""
    echo "========================================"
    echo " 错误：CPU 架构不匹配"
    echo "========================================"
    echo "您的麒麟系统: $(normalize_arch "$host") ($host)"
    echo "当前程序包:   ${2:-未知}"
    echo ""
    echo "常见原因：飞腾/鲲鹏等 ARM 电脑安装了 x86_64 版本。"
    echo ""
    echo "解决办法："
    echo "  1. 下载与您 CPU 对应的版本："
    echo "     - Intel/AMD 电脑 → PdfToWord-Kylin-x86_64.run"
    echo "     - 飞腾/鲲鹏等 ARM → PdfToWord-Kylin-aarch64.run"
    echo ""
    echo "  2. 或使用 Python 源码安装（任意架构）："
    echo "     将完整 pdf-to-word 项目拷到本机后执行："
    echo "     chmod +x installer/linux/install-kylin.sh"
    echo "     ./installer/linux/install-kylin.sh"
    echo ""
    echo "查看本机架构: uname -m"
    echo "查看程序架构: file PdfToWord"
}
