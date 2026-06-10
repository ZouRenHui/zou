"""手机相机风格的圆形录制按钮。"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable


class RecordButton(tk.Frame):
    SIZE = 88
    RING_WIDTH = 4
    INNER_RADIUS = 26
    STOP_HALF = 14

    IDLE_FILL = "#ff2d55"
    IDLE_ACTIVE = "#e0244a"
    DISABLED_FILL = "#c8c8c8"
    RING_COLOR = "#b8b8b8"

    def __init__(
        self,
        parent: tk.Misc,
        command: Callable[[], None],
        *,
        bg: str | None = None,
    ) -> None:
        super().__init__(parent, bg=bg or self._parent_bg(parent))
        self._command = command
        self._recording = False
        self._enabled = True
        self._inner_id: int | None = None

        self.canvas = tk.Canvas(
            self,
            width=self.SIZE,
            height=self.SIZE,
            highlightthickness=0,
            bd=0,
            bg=self["bg"],
            cursor="hand2",
        )
        self.canvas.pack()

        cx = cy = self.SIZE // 2
        outer_r = self.SIZE // 2 - 2
        self.canvas.create_oval(
            cx - outer_r,
            cy - outer_r,
            cx + outer_r,
            cy + outer_r,
            outline=self.RING_COLOR,
            width=self.RING_WIDTH,
            fill="",
        )
        self._draw_inner()
        self.canvas.bind("<Button-1>", self._on_click)

    @staticmethod
    def _parent_bg(parent: tk.Misc) -> str:
        try:
            return str(parent.cget("background"))
        except tk.TclError:
            return "#f0f0f0"

    def _center(self) -> tuple[int, int]:
        return self.SIZE // 2, self.SIZE // 2

    def _fill(self) -> str:
        if not self._enabled:
            return self.DISABLED_FILL
        return self.IDLE_FILL

    def _draw_inner(self) -> None:
        if self._inner_id is not None:
            self.canvas.delete(self._inner_id)

        cx, cy = self._center()
        fill = self._fill()

        if self._recording:
            half = self.STOP_HALF
            self._inner_id = self.canvas.create_rectangle(
                cx - half,
                cy - half,
                cx + half,
                cy + half,
                fill=fill,
                outline=fill,
            )
        else:
            r = self.INNER_RADIUS
            self._inner_id = self.canvas.create_oval(
                cx - r,
                cy - r,
                cx + r,
                cy + r,
                fill=fill,
                outline=fill,
            )

    def _on_click(self, _event: tk.Event) -> None:
        if self._enabled:
            self._command()

    def set_recording(self, recording: bool) -> None:
        if self._recording == recording:
            return
        self._recording = recording
        self._draw_inner()

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        self.canvas.configure(cursor="hand2" if enabled else "arrow")
        self._draw_inner()
