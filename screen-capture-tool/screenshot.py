"""截屏：全屏与区域选择。"""

from __future__ import annotations

import platform
import subprocess
import tempfile
import tkinter as tk
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import mss
from PIL import Image

_IS_MACOS = platform.system() == "Darwin"


@dataclass(frozen=True)
class CaptureRegion:
    left: int
    top: int
    width: int
    height: int

    def as_mss_dict(self) -> dict[str, int]:
        return {
            "left": self.left,
            "top": self.top,
            "width": self.width,
            "height": self.height,
        }

    def as_screencapture_rect(self) -> str:
        return f"{self.left},{self.top},{self.width},{self.height}"


def _virtual_screen_bounds(root: tk.Misc | None = None) -> tuple[int, int, int, int]:
    """返回虚拟桌面 (left, top, width, height)。macOS 使用逻辑坐标（点）。"""
    if root is not None:
        root.update_idletasks()
        return (
            root.winfo_vrootx(),
            root.winfo_vrooty(),
            root.winfo_vrootwidth(),
            root.winfo_vrootheight(),
        )

    tmp = tk.Tk()
    tmp.withdraw()
    bounds = (
        tmp.winfo_vrootx(),
        tmp.winfo_vrooty(),
        tmp.winfo_vrootwidth(),
        tmp.winfo_vrootheight(),
    )
    tmp.destroy()
    return bounds


def capture_full_screen() -> Image.Image:
    if _IS_MACOS:
        return _capture_full_screen_macos()
    with mss.mss() as sct:
        shot = sct.grab(sct.monitors[0])
        return Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")


def capture_region(region: CaptureRegion) -> Image.Image:
    if _IS_MACOS:
        return _capture_region_macos(region)
    with mss.mss() as sct:
        shot = sct.grab(region.as_mss_dict())
        return Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")


def _capture_full_screen_macos() -> Image.Image:
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        path = Path(tmp.name)
    try:
        subprocess.run(
            ["screencapture", "-x", str(path)],
            check=True,
            capture_output=True,
        )
        if not path.exists() or path.stat().st_size == 0:
            raise RuntimeError("screencapture 未生成图片")
        return Image.open(path).convert("RGB")
    except FileNotFoundError as exc:
        raise RuntimeError("未找到 screencapture 命令") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            "截屏失败，请在「系统设置 → 隐私与安全性 → 屏幕录制」中"
            "允许终端或 Python 访问屏幕录制。"
        ) from exc
    finally:
        path.unlink(missing_ok=True)


def _capture_region_macos(region: CaptureRegion) -> Image.Image:
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        path = Path(tmp.name)
    try:
        subprocess.run(
            [
                "screencapture",
                "-x",
                "-R",
                region.as_screencapture_rect(),
                str(path),
            ],
            check=True,
            capture_output=True,
        )
        if not path.exists() or path.stat().st_size == 0:
            raise RuntimeError("screencapture 未生成图片")
        return Image.open(path).convert("RGB")
    except FileNotFoundError as exc:
        raise RuntimeError("未找到 screencapture 命令") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            "区域截屏失败，请确认已授予屏幕录制权限。"
        ) from exc
    finally:
        path.unlink(missing_ok=True)


class RegionSelector:
    """全屏半透明遮罩，鼠标拖拽选择区域。"""

    def __init__(
        self,
        on_complete: Callable[[CaptureRegion | None], None],
        *,
        parent: tk.Misc | None = None,
    ) -> None:
        self._on_complete = on_complete
        self._start_x = 0
        self._start_y = 0
        self._rect_id: int | None = None
        self._active = False

        if parent is None:
            raise ValueError("区域截屏需要 parent 窗口以获取正确的屏幕坐标")

        self.root = tk.Toplevel(parent)
        self.root.withdraw()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.25)
        self.root.configure(bg="black")
        self.root.bind("<Escape>", lambda _e: self._cancel())

        self._offset_x, self._offset_y, width, height = _virtual_screen_bounds(parent)

        self.root.geometry(f"{width}x{height}+{self._offset_x}+{self._offset_y}")

        self.canvas = tk.Canvas(
            self.root,
            width=width,
            height=height,
            highlightthickness=0,
            bg="black",
            cursor="crosshair",
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        hint = "拖拽选择区域，Esc 取消"
        self.canvas.create_text(
            width // 2,
            28,
            text=hint,
            fill="white",
            font=("", 14, "bold"),
        )

        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)

        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def _delayed_finish(self, region: CaptureRegion | None, *, delay_ms: int = 120) -> None:
        """在主窗口上调度收尾，避免在即将销毁的 Toplevel 上使用 after()（macOS 3.12 会报错）。"""
        parent = self.root.master
        self.root.withdraw()
        self.root.update_idletasks()
        toplevel = self.root

        def finish() -> None:
            try:
                if toplevel.winfo_exists():
                    toplevel.destroy()
            except tk.TclError:
                pass
            self._on_complete(region)

        try:
            parent.after(delay_ms, finish)
        except tk.TclError:
            finish()

    def _on_press(self, event: tk.Event) -> None:
        self._active = True
        self._start_x = event.x
        self._start_y = event.y
        if self._rect_id is not None:
            self.canvas.delete(self._rect_id)
            self._rect_id = None

    def _on_drag(self, event: tk.Event) -> None:
        if not self._active:
            return
        if self._rect_id is not None:
            self.canvas.delete(self._rect_id)
        self._rect_id = self.canvas.create_rectangle(
            self._start_x,
            self._start_y,
            event.x,
            event.y,
            outline="#4da3ff",
            width=2,
        )

    def _on_release(self, event: tk.Event) -> None:
        if not self._active:
            return
        self._active = False

        x1, y1 = self._start_x, self._start_y
        x2, y2 = event.x, event.y
        left = min(x1, x2) + self._offset_x
        top = min(y1, y2) + self._offset_y
        width = abs(x2 - x1)
        height = abs(y2 - y1)

        region = None
        if width >= 5 and height >= 5:
            region = CaptureRegion(left=left, top=top, width=width, height=height)

        self._delayed_finish(region, delay_ms=120)

    def _cancel(self) -> None:
        self._delayed_finish(None, delay_ms=80)
