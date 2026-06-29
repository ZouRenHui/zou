#!/usr/bin/env python3
"""录屏 / 截屏工具 — 图形界面。"""

from __future__ import annotations

import platform
import subprocess
import tempfile
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk

import app_log
from app_log import get_logger
from clipboard_utils import copy_image_to_clipboard
from record_button import RecordButton
from recorder import ScreenRecorder
from screenshot import RegionSelector, capture_full_screen, capture_region

_log = get_logger("gui")


class ScreenCaptureApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("录屏 / 截屏工具")
        self.root.minsize(520, 420)
        self.root.geometry("640x500")

        self.recorder = ScreenRecorder()
        self._timer_job: str | None = None
        self._closing = False
        self._last_image: Image.Image | None = None
        self._preview_photo: ImageTk.PhotoImage | None = None
        self._region_selector: RegionSelector | None = None

        self.record_status = tk.StringVar(value="就绪")
        self.record_timer = tk.StringVar(value="00:00")
        self.shot_status = tk.StringVar(value="就绪")

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        _log.info("应用启动 — 系统: %s, Python: %s",
                  platform.system(), __import__("sys").version.split()[0])

    def _schedule(self, delay_ms: int, callback) -> str | None:
        """在主窗口上安全调度 after 回调。"""
        if self._closing:
            return None
        try:
            if not self.root.winfo_exists():
                return None
            return self.root.after(delay_ms, callback)
        except tk.TclError:
            return None

    def _build_ui(self) -> None:
        pad = {"padx": 10, "pady": 6}
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, **pad)

        record_tab = ttk.Frame(notebook)
        shot_tab = ttk.Frame(notebook)
        notebook.add(record_tab, text="录屏")
        notebook.add(shot_tab, text="截屏")

        self._build_record_tab(record_tab)
        self._build_shot_tab(shot_tab)
        self._build_statusbar()

    def _build_statusbar(self) -> None:
        bar = ttk.Frame(self.root)
        bar.pack(fill=tk.X, padx=10, pady=(0, 6))
        log_path = app_log.get_log_path()
        ttk.Button(
            bar,
            text="查看日志",
            command=self._open_log,
            width=10,
        ).pack(side=tk.RIGHT)
        ttk.Label(
            bar,
            text=f"日志: {log_path}",
            foreground="#999",
            font=("", 8),
        ).pack(side=tk.LEFT, padx=(2, 0))

    def _open_log(self) -> None:
        try:
            app_log.open_log_file()
        except RuntimeError as exc:
            messagebox.showerror("日志", str(exc), parent=self.root)

    def _build_record_tab(self, parent: ttk.Frame) -> None:
        pad = {"padx": 12, "pady": 8}

        info = ttk.Label(
            parent,
            text=(
                "点击「开始录制」捕获屏幕；再次点击结束并选择保存位置。\n"
                "系统声音需安装 ffmpeg；macOS 建议配合 BlackHole 虚拟声卡。"
            ),
            wraplength=560,
            justify=tk.LEFT,
            foreground="#555",
        )
        info.pack(anchor=tk.W, **pad)

        center = ttk.Frame(parent)
        center.pack(expand=True)

        btn_wrap = ttk.Frame(center)
        btn_wrap.pack(pady=(24, 8))
        self.record_btn = RecordButton(btn_wrap, self._toggle_recording)
        self.record_btn.pack()

        ttk.Label(center, text="点击开始录制，再次点击结束", foreground="#888").pack(pady=(0, 6))
        ttk.Label(center, textvariable=self.record_timer, font=("", 28)).pack(pady=4)
        ttk.Label(center, textvariable=self.record_status, foreground="gray").pack()

    def _build_shot_tab(self, parent: ttk.Frame) -> None:
        pad = {"padx": 12, "pady": 8}

        btn_row = ttk.Frame(parent)
        btn_row.pack(fill=tk.X, **pad)
        ttk.Button(btn_row, text="全屏截屏", command=self._shot_fullscreen, width=14).pack(
            side=tk.LEFT, padx=(0, 8)
        )
        ttk.Button(btn_row, text="区域截屏", command=self._shot_region, width=14).pack(side=tk.LEFT)

        ttk.Label(
            parent,
            text="截屏后自动复制到剪贴板，可直接 Ctrl+V / Cmd+V 粘贴到编辑器。",
            foreground="#555",
            wraplength=560,
        ).pack(anchor=tk.W, **pad)

        preview_frame = ttk.LabelFrame(parent, text="预览")
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(4, 8))

        self.preview_label = ttk.Label(preview_frame, text="暂无截图", anchor=tk.CENTER)
        self.preview_label.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        action_row = ttk.Frame(parent)
        action_row.pack(fill=tk.X, padx=12, pady=(0, 10))
        ttk.Button(action_row, text="复制到剪贴板", command=self._copy_shot).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(action_row, text="保存为图片", command=self._save_shot).pack(side=tk.LEFT)
        ttk.Label(action_row, textvariable=self.shot_status, foreground="gray").pack(side=tk.RIGHT)

    # -------------------------------------------------------------- recording
    def _toggle_recording(self) -> None:
        if self.recorder.is_recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self) -> None:
        temp = Path(tempfile.gettempdir()) / f"screen_rec_{datetime.now():%Y%m%d_%H%M%S}.mp4"
        self.record_btn.set_enabled(False)
        self.record_status.set("正在启动录制…")

        def worker() -> None:
            ok, msg = self.recorder.start(temp)
            self._schedule(0, lambda: self._on_recording_started(ok, msg))

        threading.Thread(target=worker, daemon=True).start()

    def _on_recording_started(self, ok: bool, msg: str) -> None:
        self.record_btn.set_enabled(True)
        if not ok:
            _log.error("录制启动失败: %s", msg)
            self.record_status.set("就绪")
            messagebox.showerror("录屏", msg, parent=self.root)
            return
        _log.info("录制启动成功: %s", msg)
        self.record_btn.set_recording(True)
        self.record_status.set(msg)
        self._start_timer()

    def _stop_recording(self) -> None:
        self._stop_timer()
        self.record_btn.set_enabled(False)
        self.record_status.set("正在保存…")

        def worker() -> None:
            path = self.recorder.stop()
            self._schedule(0, lambda: self._on_recording_stopped(path))

        threading.Thread(target=worker, daemon=True).start()

    def _on_recording_stopped(self, temp_path: Path | None) -> None:
        self.record_btn.set_recording(False)
        self.record_btn.set_enabled(True)
        self.record_timer.set("00:00")

        if temp_path is None or not temp_path.exists() or temp_path.stat().st_size == 0:
            self.record_status.set("录制失败或文件为空")
            detail = self.recorder.last_error
            _log.error("录制文件无效 — 路径: %s, 错误: %s", temp_path, detail)
            msg = "未能生成录制文件。"
            if detail:
                msg += f"\n\nffmpeg 错误：{detail}"
            msg += "\n\n建议：\n1. 确认 ffmpeg 在 PATH 中（ffmpeg -version）\n2. 若仅需画面，程序会自动回退到内置录制\n3. 录制系统声音需在 Windows 声音设置中启用「立体声混音」"
            messagebox.showerror("录屏", msg, parent=self.root)
            return

        default_name = f"录屏_{datetime.now():%Y%m%d_%H%M%S}.mp4"
        save_path = filedialog.asksaveasfilename(
            parent=self.root,
            title="保存录屏",
            defaultextension=".mp4",
            initialfile=default_name,
            filetypes=[("MP4 视频", "*.mp4"), ("所有文件", "*.*")],
        )
        if not save_path:
            self.record_status.set("已取消保存（临时文件已保留）")
            return

        try:
            dest = Path(save_path)
            dest.write_bytes(temp_path.read_bytes())
            temp_path.unlink(missing_ok=True)
            _log.info("录制文件已保存: %s (%d KB)", dest, dest.stat().st_size // 1024)
            self.record_status.set(f"已保存：{dest.name}")
            messagebox.showinfo("录屏", f"已保存到\n{dest}", parent=self.root)
        except OSError as exc:
            _log.error("录制文件保存失败: %s", exc)
            self.record_status.set("保存失败")
            messagebox.showerror("录屏", f"保存失败：{exc}", parent=self.root)

    def _start_timer(self) -> None:
        self._tick_timer()

    def _tick_timer(self) -> None:
        if self._closing or not self.recorder.is_recording:
            return
        elapsed = int(self.recorder.elapsed_seconds())
        mins, secs = divmod(elapsed, 60)
        self.record_timer.set(f"{mins:02d}:{secs:02d}")
        self._timer_job = self._schedule(500, self._tick_timer)

    def _stop_timer(self) -> None:
        if self._timer_job is None:
            return
        try:
            if self.root.winfo_exists():
                self.root.after_cancel(self._timer_job)
        except (tk.TclError, ValueError, AttributeError):
            pass
        self._timer_job = None

    # --------------------------------------------------------------- screenshot
    def _hide_for_capture(self) -> None:
        """完全隐藏本工具窗口，避免截到自身界面。"""
        self.root.withdraw()
        self.root.update_idletasks()
        self.root.update()

    def _shot_fullscreen(self) -> None:
        self._hide_for_capture()
        # 等待窗口管理器刷新，确保前景应用画面已显示
        self._schedule(350, self._do_fullscreen_capture)

    def _do_fullscreen_capture(self) -> None:
        try:
            image = capture_full_screen()
        except Exception as exc:
            self.root.deiconify()
            self._show_capture_error(exc)
            return
        self.root.deiconify()
        self._show_capture_result(image)

    def _shot_region(self) -> None:
        self._hide_for_capture()
        self._schedule(150, self._open_region_selector)

    def _open_region_selector(self) -> None:
        def on_region(region) -> None:
            if region is None:
                self.root.deiconify()
                self.shot_status.set("已取消区域选择")
                return
            # 遮罩关闭后再延迟一帧，确保截到真实前景画面
            self._schedule(150, lambda: self._do_region_capture(region))

        self._region_selector = RegionSelector(on_region, parent=self.root)

    def _do_region_capture(self, region) -> None:
        try:
            image = capture_region(region)
        except Exception as exc:
            self.root.deiconify()
            self._show_capture_error(exc)
            return
        self.root.deiconify()
        self._show_capture_result(image)

    def _show_capture_result(self, image: Image.Image) -> None:
        self._last_image = image
        self._update_preview(image)
        try:
            copy_image_to_clipboard(image)
            self.shot_status.set("已复制到剪贴板，可直接粘贴")
        except Exception as exc:
            _log.warning("截图成功但复制剪贴板失败: %s", exc)
            self.shot_status.set("复制到剪贴板失败")
            messagebox.showwarning("截屏", f"截图成功，但复制失败：{exc}", parent=self.root)

    def _show_capture_error(self, exc: Exception) -> None:
        _log.error("截屏失败: %s", exc)
        msg = str(exc)
        if platform.system() == "Darwin" and messagebox.askyesno(
            "截屏失败",
            f"{msg}\n\n是否打开「屏幕录制」权限设置？",
            parent=self.root,
        ):
            subprocess.run(
                [
                    "open",
                    "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture",
                ],
                check=False,
            )
        else:
            messagebox.showerror("截屏", msg, parent=self.root)

    def _update_preview(self, image: Image.Image) -> None:
        max_w, max_h = 560, 280
        preview = image.copy()
        preview.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
        self._preview_photo = ImageTk.PhotoImage(preview)
        self.preview_label.configure(image=self._preview_photo, text="")

    def _copy_shot(self) -> None:
        if self._last_image is None:
            messagebox.showinfo("截屏", "请先截屏。", parent=self.root)
            return
        try:
            copy_image_to_clipboard(self._last_image)
            self.shot_status.set("已复制到剪贴板")
        except Exception as exc:
            messagebox.showerror("截屏", f"复制失败：{exc}", parent=self.root)

    def _save_shot(self) -> None:
        if self._last_image is None:
            messagebox.showinfo("截屏", "请先截屏。", parent=self.root)
            return
        default_name = f"截图_{datetime.now():%Y%m%d_%H%M%S}.png"
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title="保存截图",
            defaultextension=".png",
            initialfile=default_name,
            filetypes=[("PNG 图片", "*.png"), ("JPEG 图片", "*.jpg;*.jpeg"), ("所有文件", "*.*")],
        )
        if not path:
            return
        try:
            dest = Path(path)
            fmt = "JPEG" if dest.suffix.lower() in {".jpg", ".jpeg"} else "PNG"
            img = self._last_image
            if fmt == "JPEG" and img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            img.save(dest, fmt)
            self.shot_status.set(f"已保存：{dest.name}")
        except OSError as exc:
            messagebox.showerror("截屏", f"保存失败：{exc}", parent=self.root)

    def _on_close(self) -> None:
        if self.recorder.is_recording:
            if not messagebox.askyesno(
                "退出",
                "正在录制，确定要退出吗？录制内容将丢失。",
                parent=self.root,
            ):
                return
            self.recorder.stop()
        self._closing = True
        self._stop_timer()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    ScreenCaptureApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
