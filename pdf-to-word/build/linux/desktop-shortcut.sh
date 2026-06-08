#!/usr/bin/env bash
# 查找桌面目录并在桌面 / 应用菜单创建 .desktop 快捷方式（麒麟 UKUI 兼容）

find_desktop_dirs() {
    local dirs=() dir seen="|"

    if command -v xdg-user-dir >/dev/null 2>&1; then
        dir="$(xdg-user-dir DESKTOP 2>/dev/null || true)"
        if [ -n "$dir" ] && [ -d "$dir" ]; then
            dirs+=("$dir")
            seen="${seen}${dir}|"
        fi
    fi

    if [ -f "${HOME}/.config/user-dirs.dirs" ]; then
        # shellcheck disable=SC1091
        source "${HOME}/.config/user-dirs.dirs"
        dir="${XDG_DESKTOP_DIR:-$HOME/Desktop}"
        dir="${dir/#\$HOME/$HOME}"
        if [ -d "$dir" ] && [[ "$seen" != *"|${dir}|"* ]]; then
            dirs+=("$dir")
            seen="${seen}${dir}|"
        fi
    fi

    for name in "桌面" "Desktop"; do
        dir="${HOME}/${name}"
        if [ -d "$dir" ] && [[ "$seen" != *"|${dir}|"* ]]; then
            dirs+=("$dir")
            seen="${seen}${dir}|"
        fi
    done

    if [ "${#dirs[@]}" -gt 0 ]; then
        printf '%s\n' "${dirs[@]}"
    fi
}

trust_desktop_file() {
    local file="$1"
    chmod +x "$file"
    if command -v gio >/dev/null 2>&1; then
        gio set "$file" metadata::trusted true 2>/dev/null || true
    fi
}

# 参数: menu_file app_id [app_name]
install_menu_and_desktop_shortcuts() {
    local menu_file="$1"
    local app_id="$2"
    local app_name="${3:-PDF 工具箱}"
    local menu_dir="${HOME}/.local/share/applications"
    local desktop_linked=false dir target

    mkdir -p "$menu_dir"
    trust_desktop_file "$menu_file"

    while IFS= read -r dir; do
        [ -z "$dir" ] && continue
        target="${dir}/${app_id}.desktop"
        cp "$menu_file" "$target"
        trust_desktop_file "$target"
        echo "[OK] 桌面快捷方式: $target"
        desktop_linked=true
    done < <(find_desktop_dirs)

    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database "$menu_dir" 2>/dev/null || true
    fi

    if $desktop_linked; then
        echo "[OK] 应用菜单: ${menu_dir}/${app_id}.desktop"
        return 0
    fi

    echo "[警告] 未找到桌面目录（已检查 xdg-user-dir、~/桌面、~/Desktop）"
    echo "       应用菜单快捷方式: ${menu_file}"
    echo "       请手动创建桌面快捷方式，或执行: ./install-kylin-python.sh --shortcut-only"
    return 1
}
