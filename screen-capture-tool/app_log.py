"""集中式日志配置与 Windows 诊断支持。"""

from __future__ import annotations

import logging
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import threading
import traceback
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

_APP_NAME = "screen-capture-tool"
_MAX_BYTES = 5 * 1024 * 1024  # 5 MB per file
_BACKUP_COUNT = 3
_hooks_installed = False
_session_header_written = False
_original_excepthook = sys.excepthook
_original_threading_excepthook = getattr(threading, "excepthook", None)


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def get_log_dir() -> Path:
    system = platform.system()
    if system == "Windows":
        base = Path.home() / "AppData" / "Local" / _APP_NAME / "logs"
    elif system == "Darwin":
        base = Path.home() / "Library" / "Logs" / _APP_NAME
    else:
        base = Path.home() / ".local" / "share" / _APP_NAME / "logs"
    try:
        base.mkdir(parents=True, exist_ok=True)
        probe = base / ".write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return base
    except OSError:
        fallback = Path(tempfile.gettempdir()) / _APP_NAME / "logs"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


def get_log_path() -> Path:
    return get_log_dir() / "app.log"


def get_crash_log_path() -> Path:
    return get_log_dir() / "crash.log"


def setup() -> None:
    global _session_header_written
    root = logging.getLogger(_APP_NAME)
    if root.handlers:
        return
    root.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)-5s] [%(threadName)s] %(name)s — %(message)s",
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
        sys.stderr.write(f"[{_APP_NAME}] 无法创建日志文件: {exc}\n")

    if not _session_header_written:
        _write_session_header(root)
        _session_header_written = True


def _write_session_header(logger: logging.Logger) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    bar = "=" * 72
    logger.info(bar)
    logger.info("应用启动 %s", now)
    logger.info("日志目录: %s", get_log_dir())
    logger.info(bar)


def get_logger(module: str) -> logging.Logger:
    setup()
    return logging.getLogger(f"{_APP_NAME}.{module}")


def log_exception(
    logger: logging.Logger,
    message: str,
    *,
    exc: BaseException | None = None,
) -> None:
    """记录带完整堆栈的异常信息。"""
    if exc is not None:
        logger.error("%s: %s", message, exc, exc_info=(type(exc), exc, exc.__traceback__))
    else:
        logger.error(message, exc_info=True)


def write_crash_report(title: str, exc_info=None) -> None:
    """将未捕获异常写入独立的 crash.log。"""
    if exc_info is None:
        exc_info = sys.exc_info()
    if exc_info == (None, None, None):
        return

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "=" * 72,
        f"崩溃报告 {now}",
        f"标题: {title}",
        f"日志目录: {get_log_dir()}",
        f"可执行文件: {sys.executable}",
        "-" * 72,
        "".join(traceback.format_exception(*exc_info)),
        "=" * 72,
        "",
    ]
    try:
        with open(get_crash_log_path(), "a", encoding="utf-8") as fh:
            fh.write("\n".join(lines))
    except OSError:
        pass

    root = logging.getLogger(_APP_NAME)
    if root.handlers:
        root.critical("未捕获异常已写入 %s — %s", get_crash_log_path(), title, exc_info=exc_info)


def install_exception_hooks() -> None:
    """安装全局异常钩子，确保崩溃信息写入日志。"""
    global _hooks_installed
    if _hooks_installed:
        return
    _hooks_installed = True
    setup()

    def _handle_exception(exc_type, exc_value, exc_tb) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            _original_excepthook(exc_type, exc_value, exc_tb)
            return
        logger = get_logger("crash")
        logger.critical(
            "未捕获的主线程异常",
            exc_info=(exc_type, exc_value, exc_tb),
        )
        write_crash_report("未捕获的主线程异常", (exc_type, exc_value, exc_tb))
        _original_excepthook(exc_type, exc_value, exc_tb)

    sys.excepthook = _handle_exception

    if hasattr(threading, "excepthook"):
        def _handle_thread_exception(args) -> None:
            logger = get_logger("crash")
            logger.critical(
                "未捕获的线程异常 — 线程: %s",
                getattr(args, "thread", None),
                exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
            )
            write_crash_report(
                f"未捕获的线程异常: {getattr(args.thread, 'name', 'unknown')}",
                (args.exc_type, args.exc_value, args.exc_traceback),
            )
            if _original_threading_excepthook is not None:
                _original_threading_excepthook(args)

        threading.excepthook = _handle_thread_exception


def run_subprocess_text(
    args: list[str],
    *,
    timeout: float = 15.0,
) -> str:
    """运行子进程并以 UTF-8 容错解码输出，避免 Windows GBK 解码崩溃。"""
    kwargs: dict = {
        "capture_output": True,
        "timeout": timeout,
    }
    if platform.system() == "Windows":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    try:
        result = subprocess.run(args, **kwargs)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"<执行失败: {exc}>"

    chunks: list[str] = []
    for raw in (result.stdout, result.stderr):
        if raw:
            chunks.append(raw.decode("utf-8", errors="replace"))
    return "".join(chunks)


def _run_command(args: list[str], timeout: float = 10.0) -> str:
    output = run_subprocess_text(args, timeout=timeout)
    return output.strip() or "<无输出>"


def _windows_details(logger: logging.Logger) -> None:
    try:
        ver = sys.getwindowsversion()  # type: ignore[attr-defined]
        logger.info(
            "Windows 版本: %s.%s build %s SP %s",
            ver.major,
            ver.minor,
            ver.build,
            ver.service_pack,
        )
    except Exception as exc:
        logger.warning("无法读取 Windows 版本: %s", exc)

    logger.info("处理器架构: %s", os.environ.get("PROCESSOR_ARCHITECTURE", "unknown"))
    logger.info("用户配置目录: %s", os.environ.get("USERPROFILE", ""))
    logger.info("临时目录: %s", tempfile.gettempdir())

    try:
        import ctypes

        user32 = ctypes.windll.user32
        width = user32.GetSystemMetrics(0)
        height = user32.GetSystemMetrics(1)
        logger.info("主显示器分辨率 (GetSystemMetrics): %dx%d", width, height)
        dpi = user32.GetDpiForSystem()
        logger.info("系统 DPI: %s", dpi)
    except Exception as exc:
        logger.debug("Windows 显示信息读取失败: %s", exc)

    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        ) as key:
            apps_use_light, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            logger.info("Windows 浅色主题: %s", bool(apps_use_light))
    except OSError:
        pass


def _log_monitors(logger: logging.Logger) -> None:
    try:
        import mss

        with mss.mss() as sct:
            for index, mon in enumerate(sct.monitors):
                logger.info("显示器[%d]: %s", index, mon)
    except Exception as exc:
        logger.warning("无法枚举显示器: %s", exc)


def _log_ffmpeg(logger: logging.Logger) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        logger.warning("ffmpeg: 不在 PATH 中")
        return
    logger.info("ffmpeg 路径: %s", ffmpeg)
    version = _run_command([ffmpeg, "-version"], timeout=8)
    first_line = version.splitlines()[0] if version else version
    logger.info("ffmpeg 版本: %s", first_line)
    if platform.system() == "Windows":
        logger.debug("ffmpeg -hide_banner -list_devices true -f wasapi -i dummy:\n%s", _run_command(
            [ffmpeg, "-hide_banner", "-list_devices", "true", "-f", "wasapi", "-i", "dummy"],
            timeout=15,
        ))
        logger.debug("ffmpeg -hide_banner -list_devices true -f dshow -i dummy:\n%s", _run_command(
            [ffmpeg, "-hide_banner", "-list_devices", "true", "-f", "dshow", "-i", "dummy"],
            timeout=15,
        ))


def log_environment(logger: logging.Logger | None = None) -> None:
    """记录启动时的系统环境，便于 Windows 问题排查。"""
    logger = logger or get_logger("env")
    logger.info("-" * 48)
    logger.info("环境诊断开始")
    logger.info("平台: %s %s", platform.system(), platform.release())
    logger.info("机器: %s / %s", platform.machine(), platform.processor() or "unknown")
    logger.info("Python: %s", sys.version.replace("\n", " "))
    logger.info("可执行文件: %s", sys.executable)
    logger.info("工作目录: %s", os.getcwd())
    logger.info("打包模式 (frozen): %s", is_frozen())
    if is_frozen():
        logger.info("_MEIPASS: %s", getattr(sys, "_MEIPASS", ""))

    logger.info("命令行参数数量: %d", len(sys.argv))
    if sys.argv:
        logger.info("argv[0]: %s", sys.argv[0])

    path_entries = os.environ.get("PATH", "").split(os.pathsep)
    logger.info("PATH 条目数: %d", len(path_entries))

    for key in ("DISPLAY", "WAYLAND_DISPLAY", "SDL_VIDEODRIVER"):
        value = os.environ.get(key)
        if value:
            logger.info("%s=%s", key, value)

    if platform.system() == "Windows":
        _windows_details(logger)

    _log_monitors(logger)
    _log_ffmpeg(logger)

    try:
        import cv2

        logger.info("OpenCV: %s", cv2.__version__)
    except Exception as exc:
        logger.warning("OpenCV 不可用: %s", exc)

    try:
        from PIL import Image

        logger.info("Pillow: %s", Image.__version__)
    except Exception as exc:
        logger.warning("Pillow 不可用: %s", exc)

    logger.info("环境诊断结束")
    logger.info("-" * 48)


def open_log_file() -> None:
    """用系统默认程序打开日志文件。"""
    path = get_log_path()
    if not path.exists():
        path.write_text("", encoding="utf-8")
    system = platform.system()
    try:
        if system == "Windows":
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif system == "Darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except Exception as exc:
        raise RuntimeError(f"无法打开日志文件: {path}\n{exc}") from exc


def open_log_dir() -> None:
    """用资源管理器 / Finder 打开日志目录。"""
    directory = get_log_dir()
    system = platform.system()
    try:
        if system == "Windows":
            os.startfile(str(directory))  # type: ignore[attr-defined]
        elif system == "Darwin":
            subprocess.Popen(["open", str(directory)])
        else:
            subprocess.Popen(["xdg-open", str(directory)])
    except Exception as exc:
        raise RuntimeError(f"无法打开日志目录: {directory}\n{exc}") from exc
