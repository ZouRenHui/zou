"""跨平台将图片复制到系统剪贴板。"""

from __future__ import annotations

import io
import platform
import subprocess
import tempfile
from pathlib import Path

from PIL import Image


def copy_image_to_clipboard(image: Image.Image) -> None:
    system = platform.system()
    if system == "Darwin":
        _copy_macos(image)
    elif system == "Windows":
        _copy_windows(image)
    else:
        _copy_linux(image)


def _copy_macos(image: Image.Image) -> None:
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        path = Path(tmp.name)
    try:
        image.save(path, "PNG")
        script = f'set the clipboard to (read (POSIX file "{path}") as «class PNGf»)'
        subprocess.run(["osascript", "-e", script], check=True, capture_output=True)
    finally:
        path.unlink(missing_ok=True)


def _copy_windows(image: Image.Image) -> None:
    try:
        import win32clipboard  # type: ignore[import-untyped]
    except ImportError:
        _copy_windows_powershell(image)
        return

    output = io.BytesIO()
    image.convert("RGB").save(output, "BMP")
    data = output.getvalue()[14:]
    output.close()
    win32clipboard.OpenClipboard()
    try:
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
    finally:
        win32clipboard.CloseClipboard()


def _copy_windows_powershell(image: Image.Image) -> None:
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        path = Path(tmp.name)
    try:
        image.save(path, "PNG")
        # Escape single quotes in path (PS single-quoted string escaping)
        path_ps = str(path).replace("'", "''")
        # Use ReadAllBytes+MemoryStream to avoid Image.FromFile locking the file
        ps = (
            "Add-Type -AssemblyName System.Windows.Forms; "
            "Add-Type -AssemblyName System.Drawing; "
            f"$bytes = [System.IO.File]::ReadAllBytes('{path_ps}'); "
            "$ms = New-Object System.IO.MemoryStream(,$bytes); "
            "$img = [System.Drawing.Image]::FromStream($ms); "
            "[System.Windows.Forms.Clipboard]::SetImage($img); "
            "$img.Dispose(); $ms.Dispose()"
        )
        subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
            check=True,
            capture_output=True,
        )
    finally:
        path.unlink(missing_ok=True)


def _copy_linux(image: Image.Image) -> None:
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        path = Path(tmp.name)
    try:
        image.save(path, "PNG")
        for cmd in (
            ["xclip", "-selection", "clipboard", "-t", "image/png", "-i", str(path)],
            ["wl-copy", "-t", "image/png", str(path)],
        ):
            try:
                subprocess.run(cmd, check=True, capture_output=True)
                return
            except (FileNotFoundError, subprocess.CalledProcessError):
                continue
        raise RuntimeError("未找到 xclip 或 wl-copy，无法写入剪贴板")
    finally:
        path.unlink(missing_ok=True)
