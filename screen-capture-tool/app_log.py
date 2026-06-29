"""集中式日志配置。"""

from __future__ import annotations

import logging
import platform
import subprocess
from logging.handlers import RotatingFileHandler
from pathlib import Path

_APP_NAME = "screen-capture-tool"
_MAX_BYTES = 5 * 1024 * 1024  # 5 MB per file
_BACKUP_COUNT = 3


def get_log_path() -> Path:
    system = platform.system()
    if system == "Windows":
        base = Path.home() / "AppData" / "Local" / _APP_NAME
    elif system == "Darwin":
        base = Path.home() / "Library" / "Logs" / _APP_NAME
    else:
        base = Path.home() / ".local" / "share" / _APP_NAME / "logs"
    base.mkdir(parents=True, exist_ok=True)
    return base / "app.log"


def setup() -> None:
    root = logging.getLogger(_APP_NAME)
    if root.handlers:
        return
    root.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)-5s] %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    try:
        fh = RotatingFileHandler(
            get_log_path(),
            maxBytes=_MAX_BYTES,
            backupCount=_BACKUP_COUNT,
            encoding="utf-8",
        )
        fh.setFormatter(fmt)
        root.addHandler(fh)
    except OSError as exc:
        logging.warning("无法创建日志文件: %s", exc)


def get_logger(module: str) -> logging.Logger:
    setup()
    return logging.getLogger(f"{_APP_NAME}.{module}")


def open_log_file() -> None:
    """用系统默认程序打开日志文件。"""
    path = get_log_path()
    if not path.exists():
        path.write_text("", encoding="utf-8")
    system = platform.system()
    try:
        if system == "Windows":
            import os
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif system == "Darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except Exception as exc:
        raise RuntimeError(f"无法打开日志文件: {path}\n{exc}") from exc
