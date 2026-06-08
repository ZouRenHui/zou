#!/usr/bin/env bash
# 检测是否为银河麒麟 / openKylin 等系统

is_kylin() {
    if [ -f /etc/.kyinfo ] || [ -f /etc/kylin-build ]; then
        return 0
    fi
    if [ -f /etc/os-release ] && grep -qiE 'kylin|openkylin|银河麒麟' /etc/os-release; then
        return 0
    fi
    return 1
}
