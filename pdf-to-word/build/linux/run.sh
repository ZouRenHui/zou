#!/usr/bin/env bash
# PDF 转 Word 启动脚本（免安装版）
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR" || exit 1
exec ./PdfToWord "$@"
