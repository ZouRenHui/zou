#!/usr/bin/env bash
# 安装 PDF 工具箱所需的系统 Python / tkinter 依赖（apt / dnf / yum）
# 可被 install-kylin-python.sh 或其他安装脚本 source 或 exec

set -euo pipefail

APP_NAME="${APP_NAME:-PDF 工具箱}"

python_minor_version() {
    python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || true
}

check_tkinter() {
    local py="${1:-python3}"
    "$py" -c "import tkinter" 2>/dev/null
}

tkinter_import_error() {
    local py="${1:-python3}"
    "$py" -c "import tkinter" 2>&1 | head -3 || true
}

tk_package_installed() {
    if command -v dpkg >/dev/null 2>&1; then
        dpkg -l python3-tk 2>/dev/null | grep -q '^ii' && return 0
        local ver
        ver="$(python_minor_version)"
        if [ -n "$ver" ]; then
            dpkg -l "python${ver}-tk" 2>/dev/null | grep -q '^ii' && return 0
        fi
    fi
    return 1
}

reinstall_apt_tk_packages() {
    local ver tk_candidates=()
    ver="$(python_minor_version)"

    tk_candidates=(python3-tk python3-tkinter)
    if [ -n "$ver" ]; then
        tk_candidates=("python${ver}-tk" "python${ver}-tkinter" "${tk_candidates[@]}")
        run_privileged apt-get install -y --reinstall "python${ver}" "libpython${ver}-stdlib" 2>/dev/null || true
    fi

    echo "python3-tk 已安装但 tkinter 仍不可用，尝试修复..."
    run_privileged apt-get install -y --reinstall "${tk_candidates[@]}" || true
}

run_privileged() {
    if [ "$(id -u)" -eq 0 ]; then
        "$@"
        return $?
    fi

    if command -v pkexec >/dev/null 2>&1; then
        pkexec "$@" && return 0
    fi

    if ! command -v sudo >/dev/null 2>&1; then
        return 1
    fi

    if [ -t 0 ]; then
        sudo "$@"
        return $?
    fi

    if command -v zenity >/dev/null 2>&1; then
        local pw
        pw="$(zenity --password --title="$APP_NAME" --text="安装系统依赖需要管理员密码：" 2>/dev/null)" || return 1
        echo "$pw" | sudo -S "$@" 2>&1
        local rc=$?
        unset pw
        return "$rc"
    fi

    if command -v kdialog >/dev/null 2>&1; then
        local pw
        pw="$(kdialog --password "安装系统依赖需要管理员密码：" 2>/dev/null)" || return 1
        echo "$pw" | sudo -S "$@" 2>&1
        local rc=$?
        unset pw
        return "$rc"
    fi

    return 1
}

install_apt_deps() {
    local ver tk_candidates=()
    ver="$(python_minor_version)"

    tk_candidates=(python3-tk python3-tkinter)
    if [ -n "$ver" ]; then
        tk_candidates+=("python${ver}-tk" "python${ver}-tkinter")
    fi

    echo "检测到 apt，正在安装 Python 与 tkinter 依赖..."
    run_privileged apt-get update -qq || run_privileged apt-get update || true
    run_privileged apt-get install -y python3 python3-pip python3-venv || true

    local pkg installed=false
    for pkg in "${tk_candidates[@]}"; do
        if run_privileged apt-get install -y "$pkg"; then
            echo "[OK] 已安装: $pkg"
            installed=true
            break
        fi
    done

    if ! $installed; then
        run_privileged apt-get install -y "${tk_candidates[@]}" || true
    fi
}

install_dnf_yum_deps() {
    local pm=dnf
    command -v dnf >/dev/null 2>&1 || pm=yum

    echo "检测到 ${pm}，正在安装 Python 与 tkinter 依赖..."
    run_privileged "$pm" install -y python3 python3-pip python3-tkinter || true
    run_privileged "$pm" install -y python3-tk || true
}

install_system_python_deps() {
    if command -v apt-get >/dev/null 2>&1; then
        install_apt_deps
    elif command -v dnf >/dev/null 2>&1 || command -v yum >/dev/null 2>&1; then
        install_dnf_yum_deps
    else
        echo "[警告] 未识别包管理器（apt/dnf/yum），请手动安装 python3 与 python3-tk。"
        return 1
    fi
}

tkinter_failure_message() {
    local ver pyexe err pkg_hint=""
    ver="$(python3 --version 2>&1 || echo "未知")"
    pyexe="$(command -v python3 2>/dev/null || echo "未找到")"
    err="$(tkinter_import_error python3)"
    if ver_pkg="$(python_minor_version)"; then
        [ -n "$ver_pkg" ] && pkg_hint="\n  sudo apt-get install -y --reinstall python${ver_pkg}-tk python${ver_pkg}"
    fi

    cat <<EOF
tkinter 不可用，图形界面无法启动。

当前 Python: ${ver}
路径: ${pyexe}
$( [ -n "$err" ] && echo "错误信息: ${err}" )
$( tk_package_installed && echo "说明: python3-tk 包已安装，但 Python 仍无法加载 tkinter（常见于 libpython 版本不匹配）。" )

请手动执行：

  sudo apt-get update
  sudo apt-get install -y python3 python3-pip python3-venv python3-tk${pkg_hint}
  sudo apt-get install -y --reinstall python3-tk

验证：python3 -c "import tkinter; print('OK')"

安装完成后重新运行安装包。
EOF
}

ensure_tkinter() {
    local gui_question_fn="${1:-}"

    if check_tkinter; then
        return 0
    fi

    echo "未检测到 tkinter，准备安装系统依赖..."

    local proceed=true
    if [ -n "$gui_question_fn" ] && declare -F "$gui_question_fn" >/dev/null 2>&1; then
        if ! "$gui_question_fn" "PDF 工具箱需要系统组件 python3-tk 才能显示界面。\n\n是否现在自动安装？（需要管理员密码）"; then
            proceed=false
        fi
    elif [ ! -t 0 ]; then
        proceed=true
    fi

    if $proceed; then
        install_system_python_deps || true
        if check_tkinter; then
            echo "[OK] tkinter 已可用"
            return 0
        fi

        if tk_package_installed; then
            reinstall_apt_tk_packages || true
            if check_tkinter; then
                echo "[OK] tkinter 修复成功"
                return 0
            fi
        fi
    fi

    return 1
}
