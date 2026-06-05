#!/usr/bin/env python3
"""图片处理工具 — 图形界面。"""

from __future__ import annotations

import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox, scrolledtext, ttk

from PIL import Image, ImageOps, ImageTk

from image_processing import (
    CompressOptions,
    ConvertOptions,
    CropBox,
    RemoveWatermarkOptions,
    ResizeOptions,
    WatermarkOptions,
    add_watermark,
    compress_image,
    convert_image,
    export_ocr_docx,
    export_ocr_txt,
    process_batch_compress,
    process_batch_convert,
    process_batch_resize,
    process_batch_watermark,
    remove_watermark,
    resolve_remove_box,
    resize_image,
    save_image,
)
from ocr_engines import OcrOptions, check_ocr_environment, run_ocr
from image_utils import OUTPUT_FORMATS, QUALITY_PRESETS, collect_images, format_file_size

OCR_ENGINE_OPTIONS: dict[str, str] = {
    "PaddleOCR（高精度，推荐）": "paddle",
    "Tesseract（轻量）": "tesseract",
}

OCR_PREPROCESS_OPTIONS: dict[str, str] = {
    "自动增强（推荐）": "auto",
    "强增强（模糊/低对比）": "strong",
    "灰度 + 对比度": "grayscale",
    "二值化": "binarize",
    "不预处理（原图）": "none",
}

OCR_PSM_OPTIONS: dict[str, int] = {
    "6 — 单块文本（文档/截图）": 6,
    "3 — 自动分页": 3,
    "11 — 稀疏文字（少量文字）": 11,
    "7 — 单行文字": 7,
    "13 — 原始单行": 13,
}

POSITION_LABELS = [
    ("左上", "top-left"),
    ("上中", "top-center"),
    ("右上", "top-right"),
    ("左中", "center-left"),
    ("居中", "center"),
    ("右中", "center-right"),
    ("左下", "bottom-left"),
    ("下中", "bottom-center"),
    ("右下", "bottom-right"),
    ("平铺", "tile"),
]

REMOVE_POSITION_LABELS = [p for p in POSITION_LABELS if p[1] != "tile"]


def build_settings_panel(parent: ttk.Frame, title: str, *, width: int = 300) -> ttk.LabelFrame:
    """Right-side settings column (plain frame — no canvas, instant layout on tab switch)."""
    _ = width  # child widget widths define column size
    wrap = ttk.Frame(parent)
    wrap.pack(side=tk.RIGHT, anchor=tk.N, padx=(0, 8), pady=4)
    panel = ttk.LabelFrame(wrap, text=title)
    panel.pack(fill=tk.X, anchor=tk.N)
    return panel


def pack_tab_footer(frame: ttk.Frame) -> tuple[ttk.Frame, ttk.Frame]:
    """Pin action bar and status bar to tab bottom (call before scroll content)."""
    action = ttk.Frame(frame)
    action.pack(side=tk.BOTTOM, fill=tk.X, padx=8, pady=(4, 12))
    status = ttk.Frame(frame)
    status.pack(side=tk.BOTTOM, fill=tk.X)
    return action, status


def pack_file_list_tab_layout(frame: ttk.Frame) -> tuple[ttk.Frame, ttk.Frame, ttk.Frame]:
    """Body + top row for batch tabs: no whole-tab scroll, content hugs top."""
    body = ttk.Frame(frame)
    body.pack(fill=tk.BOTH, expand=True)
    top = ttk.Frame(body)
    top.pack(fill=tk.X, anchor=tk.N, pady=(4, 0))
    left = ttk.Frame(top)
    left.pack(side=tk.LEFT, fill=tk.Y, anchor=tk.N)
    return body, top, left


class QualityPresetMixin:
    """Reusable quality preset dropdown + custom spinbox."""

    quality_preset: tk.StringVar
    quality: tk.IntVar
    quality_spin: ttk.Spinbox

    def _build_quality_controls(self, parent: ttk.Frame, default: str = "标准 (85)") -> None:
        self.quality_preset = tk.StringVar(value=default)
        self.quality = tk.IntVar(value=QUALITY_PRESETS.get(default, 85))

        row = ttk.Frame(parent)
        row.pack(fill=tk.X, padx=8, pady=2)
        ttk.Label(row, text="压缩质量：", width=10).pack(side=tk.LEFT)
        preset_combo = ttk.Combobox(
            row,
            textvariable=self.quality_preset,
            values=[*QUALITY_PRESETS.keys(), "自定义"],
            state="readonly",
            width=14,
        )
        preset_combo.pack(side=tk.LEFT)
        preset_combo.bind("<<ComboboxSelected>>", self._on_quality_preset)

        custom_row = ttk.Frame(parent)
        custom_row.pack(fill=tk.X, padx=8, pady=2)
        ttk.Label(custom_row, text="自定义值：", width=10).pack(side=tk.LEFT)
        self.quality_spin = ttk.Spinbox(
            custom_row, from_=1, to=100, textvariable=self.quality, width=8, state=tk.DISABLED
        )
        self.quality_spin.pack(side=tk.LEFT)

    def _on_quality_preset(self, _event: object = None) -> None:
        preset = self.quality_preset.get()
        if preset == "自定义":
            self.quality_spin.config(state=tk.NORMAL)
        else:
            self.quality.set(QUALITY_PRESETS.get(preset, 85))
            self.quality_spin.config(state=tk.DISABLED)

    def _get_quality(self) -> int:
        return self.quality.get()


class FileListMixin:
    """Shared file list and output settings."""

    image_paths: list[Path]
    recursive: tk.BooleanVar
    same_dir: tk.BooleanVar
    output_dir: tk.StringVar

    def _build_file_section(self, parent: ttk.Frame) -> None:
        pad = {"padx": 8, "pady": 2}
        file_frame = ttk.LabelFrame(parent, text="图片文件")
        file_frame.pack(fill=tk.X, anchor=tk.N, **pad)

        list_frame = ttk.Frame(file_frame)
        list_frame.pack(fill=tk.X, padx=8, pady=(6, 4))

        scroll = ttk.Scrollbar(list_frame)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.file_list = tk.Listbox(
            list_frame,
            selectmode=tk.EXTENDED,
            yscrollcommand=scroll.set,
            font=("", 11),
            height=4,
        )
        self.file_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.config(command=self.file_list.yview)

        btn_row = ttk.Frame(file_frame)
        btn_row.pack(fill=tk.X, padx=8, pady=(0, 8))
        ttk.Button(btn_row, text="添加文件…", command=self._add_files).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_row, text="添加文件夹…", command=self._add_folder).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_row, text="移除选中", command=self._remove_selected).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_row, text="清空", command=self._clear_list).pack(side=tk.LEFT)

        out_frame = ttk.LabelFrame(parent, text="输出设置")
        out_frame.pack(fill=tk.X, anchor=tk.N, **pad)

        ttk.Checkbutton(
            out_frame,
            text="输出到原图同目录",
            variable=self.same_dir,
            command=self._toggle_output_dir,
        ).pack(anchor=tk.W, padx=8, pady=(8, 2))

        dir_row = ttk.Frame(out_frame)
        dir_row.pack(fill=tk.X, padx=8, pady=(2, 8))
        ttk.Label(dir_row, text="输出目录：").pack(side=tk.LEFT)
        self.output_entry = ttk.Entry(dir_row, textvariable=self.output_dir, state=tk.DISABLED)
        self.output_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)
        self.browse_btn = ttk.Button(
            dir_row, text="浏览…", command=self._pick_output_dir, state=tk.DISABLED
        )
        self.browse_btn.pack(side=tk.LEFT)

        ttk.Checkbutton(
            out_frame,
            text="添加文件夹时递归扫描子目录",
            variable=self.recursive,
        ).pack(anchor=tk.W, padx=8, pady=(0, 8))

    def _build_status_bar(self, parent: ttk.Frame) -> None:
        pad = {"padx": 8, "pady": 4}
        self.status = ttk.Label(parent, text="就绪")
        self.status.pack(anchor=tk.W, **pad)
        self.progress = ttk.Progressbar(parent, mode="determinate")
        self.progress.pack(fill=tk.X, **pad)

    def _toggle_output_dir(self) -> None:
        use_same = self.same_dir.get()
        state = tk.DISABLED if use_same else tk.NORMAL
        self.output_entry.config(state=state)
        self.browse_btn.config(state=state)
        if use_same:
            self.output_dir.set("")

    def _refresh_listbox(self) -> None:
        self.file_list.delete(0, tk.END)
        for path in self.image_paths:
            self.file_list.insert(tk.END, str(path))
        self.status.config(text=f"已添加 {len(self.image_paths)} 个图片")

    def _merge_images(self, new_paths: list[Path]) -> None:
        seen = {p.resolve() for p in self.image_paths}
        for path in new_paths:
            key = path.resolve()
            if key not in seen:
                seen.add(key)
                self.image_paths.append(path)
        self.image_paths.sort(key=lambda p: str(p).lower())
        self._refresh_listbox()

    def _add_files(self) -> None:
        paths = filedialog.askopenfilenames(
            title="选择图片",
            filetypes=[
                ("图片文件", "*.jpg *.jpeg *.png *.bmp *.gif *.webp *.tiff *.tif"),
                ("所有文件", "*.*"),
            ],
        )
        if paths:
            self._merge_images([Path(p) for p in paths])

    def _add_folder(self) -> None:
        folder = filedialog.askdirectory(title="选择包含图片的文件夹")
        if not folder:
            return
        images = collect_images([Path(folder)], self.recursive.get())
        if not images:
            messagebox.showinfo("提示", "该文件夹中未找到图片文件。")
            return
        self._merge_images(images)

    def _remove_selected(self) -> None:
        indices = list(self.file_list.curselection())
        if not indices:
            return
        for i in reversed(indices):
            del self.image_paths[i]
        self._refresh_listbox()

    def _clear_list(self) -> None:
        self.image_paths.clear()
        self._refresh_listbox()

    def _pick_output_dir(self) -> None:
        folder = filedialog.askdirectory(title="选择输出目录")
        if folder:
            self.output_dir.set(folder)
            self.same_dir.set(False)
            self._toggle_output_dir()

    def _get_output_dir(self) -> Path | None:
        if self.same_dir.get():
            return None
        text = self.output_dir.get().strip()
        return Path(text) if text else None

    def _validate_files_and_output(self) -> bool:
        if not self.image_paths:
            messagebox.showwarning("提示", "请先添加至少一张图片。")
            return False
        if not self.same_dir.get() and not self.output_dir.get().strip():
            messagebox.showwarning("提示", "请指定输出目录，或勾选「输出到原图同目录」。")
            return False
        return True

    @staticmethod
    def _reveal_in_finder(path: Path) -> None:
        path = path.resolve()
        try:
            if sys.platform == "darwin":
                subprocess.run(["open", str(path)], check=False)
            elif sys.platform == "win32":
                subprocess.run(["explorer", str(path)], check=False)
            else:
                subprocess.run(["xdg-open", str(path)], check=False)
        except OSError as exc:
            messagebox.showerror("错误", f"无法打开目录：{exc}")

    def _on_batch_done(self, summary: str, fail: int, last_output: Path | None) -> None:
        self._set_busy(False)
        self.status.config(text=summary)
        if fail:
            messagebox.showwarning("完成", summary)
        else:
            messagebox.showinfo("完成", summary)
            if last_output and messagebox.askyesno("打开目录", "是否在文件管理器中打开输出目录？"):
                self._reveal_in_finder(last_output)


class RegionSelectDialog(tk.Toplevel):
    """Modal dialog to drag-select a rectangle on an image."""

    def __init__(self, parent: tk.Widget, image_path: Path, initial: CropBox | None = None) -> None:
        super().__init__(parent)
        self.title("框选水印区域")
        self.resizable(True, True)
        self.result: CropBox | None = None
        self.image_path = image_path
        self.crop_start: tuple[int, int] | None = None
        self.crop_rect_id: int | None = None
        self.scale = 1.0
        self.photo: ImageTk.PhotoImage | None = None

        self.source = Image.open(image_path)
        if self.source.mode not in ("RGB", "RGBA"):
            self.source = self.source.convert("RGB")
        w, h = self.source.size
        if initial:
            self.crop_left = tk.IntVar(value=initial.left)
            self.crop_top = tk.IntVar(value=initial.top)
            self.crop_right = tk.IntVar(value=initial.right)
            self.crop_bottom = tk.IntVar(value=initial.bottom)
        else:
            self.crop_left = tk.IntVar(value=max(0, w - 220))
            self.crop_top = tk.IntVar(value=max(0, h - 80))
            self.crop_right = tk.IntVar(value=w)
            self.crop_bottom = tk.IntVar(value=h)

        self.transient(parent.winfo_toplevel())
        self.grab_set()

        canvas_frame = ttk.Frame(self)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self.canvas = tk.Canvas(canvas_frame, bg="#333333", cursor="crosshair", width=720, height=480)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)

        coord = ttk.Frame(self)
        coord.pack(fill=tk.X, padx=8, pady=4)
        for label, var in [
            ("左", self.crop_left),
            ("上", self.crop_top),
            ("右", self.crop_right),
            ("下", self.crop_bottom),
        ]:
            ttk.Label(coord, text=f"{label}:").pack(side=tk.LEFT, padx=(0, 2))
            ttk.Spinbox(coord, from_=0, to=20000, textvariable=var, width=7).pack(side=tk.LEFT, padx=(0, 8))

        btns = ttk.Frame(self)
        btns.pack(fill=tk.X, padx=8, pady=(0, 8))
        ttk.Button(btns, text="确定", command=self._confirm).pack(side=tk.RIGHT, padx=(6, 0))
        ttk.Button(btns, text="取消", command=self.destroy).pack(side=tk.RIGHT)

        self.after(100, self._render)
        self.wait_window()

    def _render(self) -> None:
        self.canvas.update_idletasks()
        cw = max(self.canvas.winfo_width(), 400)
        ch = max(self.canvas.winfo_height(), 300)
        img = self.source.copy()
        ratio = min(cw / img.width, ch / img.height, 1.0)
        self.scale = ratio
        disp_w = max(1, int(img.width * ratio))
        disp_h = max(1, int(img.height * ratio))
        shown = img.resize((disp_w, disp_h), Image.Resampling.LANCZOS)
        self.photo = ImageTk.PhotoImage(shown)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
        self._draw_box()

    def _draw_box(self) -> None:
        if self.crop_rect_id:
            self.canvas.delete(self.crop_rect_id)
        l, t, r, b = self.crop_left.get(), self.crop_top.get(), self.crop_right.get(), self.crop_bottom.get()
        self.crop_rect_id = self.canvas.create_rectangle(
            l * self.scale, t * self.scale, r * self.scale, b * self.scale, outline="#00ff88", width=2
        )

    def _canvas_to_image(self, x: int, y: int) -> tuple[int, int]:
        return int(x / self.scale), int(y / self.scale)

    def _on_press(self, event: tk.Event) -> None:
        self.crop_start = (event.x, event.y)

    def _on_drag(self, event: tk.Event) -> None:
        if not self.crop_start:
            return
        if self.crop_rect_id:
            self.canvas.delete(self.crop_rect_id)
        x0, y0 = self.crop_start
        self.crop_rect_id = self.canvas.create_rectangle(x0, y0, event.x, event.y, outline="#00ff88", width=2)

    def _on_release(self, event: tk.Event) -> None:
        if not self.crop_start:
            return
        x0, y0 = self.crop_start
        left, top = self._canvas_to_image(min(x0, event.x), min(y0, event.y))
        right, bottom = self._canvas_to_image(max(x0, event.x), max(y0, event.y))
        w, h = self.source.size
        self.crop_left.set(max(0, left))
        self.crop_top.set(max(0, top))
        self.crop_right.set(min(w, right))
        self.crop_bottom.set(min(h, bottom))
        self.crop_start = None

    def _confirm(self) -> None:
        self.result = CropBox(
            self.crop_left.get(),
            self.crop_top.get(),
            self.crop_right.get(),
            self.crop_bottom.get(),
        )
        self.destroy()


class WatermarkTab(FileListMixin):
    def __init__(self, parent: ttk.Notebook, app: ImageToolApp) -> None:
        self.app = app
        self.frame = ttk.Frame(parent)
        parent.add(self.frame, text="水印")

        self.image_paths: list[Path] = []
        self.recursive = tk.BooleanVar(value=False)
        self.same_dir = tk.BooleanVar(value=True)
        self.output_dir = tk.StringVar()
        self._busy = False

        self.tab_action = tk.StringVar(value="add")
        self.wm_mode = tk.StringVar(value="text")
        self.wm_text = tk.StringVar(value="© 水印")
        self.wm_logo = tk.StringVar()
        self.wm_font_size = tk.IntVar(value=36)
        self.wm_opacity = tk.DoubleVar(value=0.5)
        self.wm_margin = tk.IntVar(value=20)
        self.wm_logo_scale = tk.DoubleVar(value=0.2)
        self.wm_color = (255, 255, 255)

        self.rm_region_mode = tk.StringVar(value="preset")
        self.rm_region_w = tk.IntVar(value=220)
        self.rm_region_h = tk.IntVar(value=80)
        self.rm_margin = tk.IntVar(value=20)
        self.rm_left = tk.IntVar(value=0)
        self.rm_top = tk.IntVar(value=0)
        self.rm_right = tk.IntVar(value=220)
        self.rm_bottom = tk.IntVar(value=80)
        self.rm_radius = tk.IntVar(value=5)
        self.rm_expand = tk.IntVar(value=2)
        self.rm_method = tk.StringVar(value="telea")

        self._build_ui()

    def _build_ui(self) -> None:
        action, bottom = pack_tab_footer(self.frame)
        self.run_btn = make_action_button(action, text="添加水印", command=self._start, width=14)
        self.run_btn.pack(side=tk.LEFT)
        self._build_status_bar(bottom)

        _body, top, left = pack_file_list_tab_layout(self.frame)
        self._build_file_section(left)

        self.right_panel = build_settings_panel(top, "水印设置", width=300)

        mode_row = ttk.Frame(self.right_panel)
        mode_row.pack(fill=tk.X, padx=8, pady=(8, 4))
        ttk.Radiobutton(
            mode_row, text="添加水印", variable=self.tab_action, value="add", command=self._toggle_action
        ).pack(side=tk.LEFT, padx=(0, 12))
        ttk.Radiobutton(
            mode_row, text="去除水印", variable=self.tab_action, value="remove", command=self._toggle_action
        ).pack(side=tk.LEFT)

        self.add_frame = ttk.Frame(self.right_panel)
        self.add_frame.pack(fill=tk.X, anchor=tk.N)
        self._build_add_settings(self.add_frame)

        self.remove_frame = ttk.Frame(self.right_panel)
        self._build_remove_settings(self.remove_frame)

        self._toggle_action()

    def _build_add_settings(self, parent: ttk.Frame) -> None:
        ttk.Radiobutton(parent, text="文字水印", variable=self.wm_mode, value="text").pack(anchor=tk.W, padx=8, pady=2)
        ttk.Radiobutton(parent, text="Logo 水印", variable=self.wm_mode, value="logo").pack(anchor=tk.W, padx=8, pady=2)

        text_row = ttk.Frame(parent)
        text_row.pack(fill=tk.X, padx=8, pady=4)
        ttk.Label(text_row, text="文字：").pack(side=tk.LEFT)
        ttk.Entry(text_row, textvariable=self.wm_text, width=24).pack(side=tk.LEFT, fill=tk.X, expand=True)

        logo_row = ttk.Frame(parent)
        logo_row.pack(fill=tk.X, padx=8, pady=4)
        ttk.Label(logo_row, text="Logo：").pack(side=tk.LEFT)
        ttk.Entry(logo_row, textvariable=self.wm_logo, width=18).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        ttk.Button(logo_row, text="…", width=3, command=self._pick_logo).pack(side=tk.LEFT)

        ttk.Button(parent, text="选择文字颜色…", command=self._pick_color).pack(anchor=tk.W, padx=8, pady=4)

        self._spin_row(parent, "字号", self.wm_font_size, 8, 200)
        self._spin_row(parent, "透明度", self.wm_opacity, 0.1, 1.0, increment=0.1)
        self._spin_row(parent, "边距", self.wm_margin, 0, 200)
        self._spin_row(parent, "Logo 比例", self.wm_logo_scale, 0.05, 1.0, increment=0.05)

        pos_frame = ttk.Frame(parent)
        pos_frame.pack(fill=tk.X, padx=8, pady=4)
        ttk.Label(pos_frame, text="位置：").pack(side=tk.LEFT)
        pos_combo = ttk.Combobox(pos_frame, state="readonly", width=16)
        pos_combo["values"] = [p[0] for p in POSITION_LABELS]
        pos_combo.pack(side=tk.LEFT, padx=4)
        pos_combo.current(8)
        self._pos_map = {label: key for label, key in POSITION_LABELS}
        self._pos_combo = pos_combo

    def _build_remove_settings(self, parent: ttk.Frame) -> None:
        ttk.Label(
            parent,
            text="框选水印所在区域，使用图像修复去除。\n适合固定位置的半透明文字/Logo。",
            foreground="gray",
            justify=tk.LEFT,
        ).pack(anchor=tk.W, padx=8, pady=(8, 4))

        ttk.Radiobutton(
            parent, text="按位置估算区域", variable=self.rm_region_mode, value="preset"
        ).pack(anchor=tk.W, padx=8, pady=2)
        ttk.Radiobutton(
            parent, text="自定义像素区域", variable=self.rm_region_mode, value="custom"
        ).pack(anchor=tk.W, padx=8, pady=2)

        pos_frame = ttk.Frame(parent)
        pos_frame.pack(fill=tk.X, padx=8, pady=4)
        ttk.Label(pos_frame, text="位置：").pack(side=tk.LEFT)
        rm_pos_combo = ttk.Combobox(pos_frame, state="readonly", width=16)
        rm_pos_combo["values"] = [p[0] for p in REMOVE_POSITION_LABELS]
        rm_pos_combo.pack(side=tk.LEFT, padx=4)
        rm_pos_combo.current(8)
        self._rm_pos_map = {label: key for label, key in REMOVE_POSITION_LABELS}
        self._rm_pos_combo = rm_pos_combo

        self._spin_row(parent, "区域宽", self.rm_region_w, 10, 5000)
        self._spin_row(parent, "区域高", self.rm_region_h, 10, 5000)
        self._spin_row(parent, "边距", self.rm_margin, 0, 500)

        custom = ttk.LabelFrame(parent, text="自定义区域（像素）")
        custom.pack(fill=tk.X, padx=8, pady=4)
        for label, var in [
            ("左", self.rm_left),
            ("上", self.rm_top),
            ("右", self.rm_right),
            ("下", self.rm_bottom),
        ]:
            row = ttk.Frame(custom)
            row.pack(fill=tk.X, padx=8, pady=2)
            ttk.Label(row, text=f"{label}：", width=4).pack(side=tk.LEFT)
            ttk.Spinbox(row, from_=0, to=20000, textvariable=var, width=8).pack(side=tk.LEFT)

        ttk.Button(parent, text="在预览中框选…", command=self._pick_region).pack(anchor=tk.W, padx=8, pady=6)

        self._spin_row(parent, "修复半径", self.rm_radius, 1, 30)
        self._spin_row(parent, "边缘扩展", self.rm_expand, 0, 10)

        method_row = ttk.Frame(parent)
        method_row.pack(fill=tk.X, padx=8, pady=4)
        ttk.Label(method_row, text="算法：").pack(side=tk.LEFT)
        ttk.Radiobutton(method_row, text="Telea（默认）", variable=self.rm_method, value="telea").pack(side=tk.LEFT, padx=4)
        ttk.Radiobutton(method_row, text="Navier-Stokes", variable=self.rm_method, value="ns").pack(side=tk.LEFT)

    def _toggle_action(self) -> None:
        if self.tab_action.get() == "add":
            self.remove_frame.pack_forget()
            self.add_frame.pack(fill=tk.X, anchor=tk.N)
            self.right_panel.config(text="添加水印")
            self.run_btn.config(text="添加水印")
        else:
            self.add_frame.pack_forget()
            self.remove_frame.pack(fill=tk.X, anchor=tk.N)
            self.right_panel.config(text="去除水印")
            self.run_btn.config(text="去除水印")

    def _spin_row(
        self,
        parent: ttk.Frame,
        label: str,
        var: tk.Variable,
        from_: float,
        to: float,
        increment: float = 1.0,
    ) -> None:
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, padx=8, pady=2)
        ttk.Label(row, text=f"{label}：", width=8).pack(side=tk.LEFT)
        ttk.Spinbox(row, from_=from_, to=to, increment=increment, textvariable=var, width=10).pack(side=tk.LEFT)

    def _pick_logo(self) -> None:
        path = filedialog.askopenfilename(
            title="选择 Logo",
            filetypes=[("图片", "*.png *.jpg *.jpeg *.gif *.webp *.bmp"), ("所有文件", "*.*")],
        )
        if path:
            self.wm_logo.set(path)

    def _pick_color(self) -> None:
        rgb, _ = colorchooser.askcolor(color="#ffffff", title="水印文字颜色")
        if rgb:
            self.wm_color = (int(rgb[0]), int(rgb[1]), int(rgb[2]))

    def _pick_region(self) -> None:
        if not self.image_paths:
            messagebox.showwarning("提示", "请先添加一张图片。")
            return
        path = self.image_paths[0]
        initial = CropBox(self.rm_left.get(), self.rm_top.get(), self.rm_right.get(), self.rm_bottom.get())
        dialog = RegionSelectDialog(self.frame, path, initial)
        if dialog.result:
            self.rm_region_mode.set("custom")
            self.rm_left.set(dialog.result.left)
            self.rm_top.set(dialog.result.top)
            self.rm_right.set(dialog.result.right)
            self.rm_bottom.set(dialog.result.bottom)

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.run_btn.config(state=tk.DISABLED if busy else tk.NORMAL)

    def _get_add_options(self) -> WatermarkOptions:
        pos_label = self._pos_combo.get()
        position = self._pos_map.get(pos_label, "bottom-right")
        return WatermarkOptions(
            mode=self.wm_mode.get(),  # type: ignore[arg-type]
            text=self.wm_text.get(),
            logo_path=Path(self.wm_logo.get()) if self.wm_logo.get().strip() else None,
            font_size=self.wm_font_size.get(),
            opacity=self.wm_opacity.get(),
            position=position,  # type: ignore[arg-type]
            margin=self.wm_margin.get(),
            color=self.wm_color,
            logo_scale=self.wm_logo_scale.get(),
        )

    def _get_remove_options(self) -> RemoveWatermarkOptions:
        custom = CropBox(self.rm_left.get(), self.rm_top.get(), self.rm_right.get(), self.rm_bottom.get())
        return RemoveWatermarkOptions(
            box=custom,
            inpaint_radius=self.rm_radius.get(),
            method=self.rm_method.get(),  # type: ignore[arg-type]
            mask_expand=self.rm_expand.get(),
        )

    def _resolve_remove_box(self, src: Path) -> CropBox:
        pos_label = self._rm_pos_combo.get()
        position = self._rm_pos_map.get(pos_label, "bottom-right")
        custom = CropBox(self.rm_left.get(), self.rm_top.get(), self.rm_right.get(), self.rm_bottom.get())
        return resolve_remove_box(
            src,
            preset=self.rm_region_mode.get() == "preset",
            position=position,  # type: ignore[arg-type]
            margin=self.rm_margin.get(),
            region_w=self.rm_region_w.get(),
            region_h=self.rm_region_h.get(),
            custom_box=custom,
        )

    def _start(self) -> None:
        if self._busy or not self._validate_files_and_output():
            return
        self._set_busy(True)
        self.progress["value"] = 0
        self.progress["maximum"] = len(self.image_paths)
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self) -> None:
        output = self._get_output_dir()
        ok, fail = 0, 0
        last: Path | None = None
        is_remove = self.tab_action.get() == "remove"

        try:
            for i, src in enumerate(self.image_paths, start=1):
                self.frame.after(
                    0,
                    lambda n=i, p=src: self.status.config(text=f"处理中 ({n}/{len(self.image_paths)}): {p.name}"),
                )
                try:
                    if is_remove:
                        from image_utils import resolve_output_path

                        options = self._get_remove_options()
                        box = self._resolve_remove_box(src)
                        per_opts = RemoveWatermarkOptions(
                            box=box,
                            inpaint_radius=options.inpaint_radius,
                            method=options.method,
                            mask_expand=options.mask_expand,
                        )
                        suffix = "_unwatermarked"
                        dest = resolve_output_path(src, output, batch_mode=len(self.image_paths) > 1, suffix=suffix)
                        remove_watermark(src, dest, per_opts)
                    elif len(self.image_paths) == 1:
                        from image_utils import resolve_output_path

                        dest = resolve_output_path(src, output, batch_mode=False, suffix="_watermarked")
                        add_watermark(src, dest, self._get_add_options())
                    else:
                        dest = process_batch_watermark([src], output, self._get_add_options())[0]
                    last = dest.parent
                    ok += 1
                except Exception as exc:  # noqa: BLE001
                    fail += 1
                    self.frame.after(0, lambda m=f"失败: {src.name} ({exc})": messagebox.showwarning("错误", m))
                self.frame.after(0, lambda v=i: self.progress.configure(value=v))
        except Exception as exc:  # noqa: BLE001
            self.frame.after(0, lambda: messagebox.showerror("错误", str(exc)))
            fail += 1

        action = "去水印" if is_remove else "水印"
        summary = f"{action}完成：成功 {ok}，失败 {fail}"
        self.frame.after(0, lambda: self._on_batch_done(summary, fail, last))


class ResizeTab(FileListMixin, QualityPresetMixin):
    def __init__(self, parent: ttk.Notebook, app: ImageToolApp) -> None:
        self.app = app
        self.frame = ttk.Frame(parent)
        parent.add(self.frame, text="调整尺寸")

        self.image_paths: list[Path] = []
        self.recursive = tk.BooleanVar(value=False)
        self.same_dir = tk.BooleanVar(value=True)
        self.output_dir = tk.StringVar()
        self._busy = False

        self.resize_mode = tk.StringVar(value="max_side")
        self.width = tk.IntVar(value=1920)
        self.height = tk.IntVar(value=1080)
        self.max_side = tk.IntVar(value=1920)
        self.keep_aspect = tk.BooleanVar(value=True)

        self._build_ui()

    def _build_ui(self) -> None:
        action, bottom = pack_tab_footer(self.frame)
        self.run_btn = make_action_button(action, text="调整尺寸", command=self._start, width=14)
        self.run_btn.pack(side=tk.LEFT)
        self._build_status_bar(bottom)

        _body, top, left = pack_file_list_tab_layout(self.frame)
        self._build_file_section(left)

        right = build_settings_panel(top, "尺寸设置", width=280)

        ttk.Radiobutton(right, text="限制最大边长", variable=self.resize_mode, value="max_side").pack(
            anchor=tk.W, padx=8, pady=2
        )
        ttk.Radiobutton(right, text="指定宽度 × 高度", variable=self.resize_mode, value="wh").pack(
            anchor=tk.W, padx=8, pady=2
        )
        ttk.Radiobutton(right, text="仅指定宽度", variable=self.resize_mode, value="width").pack(
            anchor=tk.W, padx=8, pady=2
        )
        ttk.Radiobutton(right, text="仅指定高度", variable=self.resize_mode, value="height").pack(
            anchor=tk.W, padx=8, pady=2
        )

        for label, var in [("最大边长", self.max_side), ("宽度", self.width), ("高度", self.height)]:
            row = ttk.Frame(right)
            row.pack(fill=tk.X, padx=8, pady=2)
            ttk.Label(row, text=f"{label}：", width=10).pack(side=tk.LEFT)
            ttk.Spinbox(row, from_=1, to=10000, textvariable=var, width=10).pack(side=tk.LEFT)

        self._build_quality_controls(right, default="高质量 (92)")

        ttk.Checkbutton(right, text="保持宽高比（指定宽高时）", variable=self.keep_aspect).pack(
            anchor=tk.W, padx=8, pady=8
        )

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.run_btn.config(state=tk.DISABLED if busy else tk.NORMAL)

    def _get_options(self) -> ResizeOptions:
        q = self._get_quality()
        mode = self.resize_mode.get()
        if mode == "max_side":
            return ResizeOptions(max_side=self.max_side.get(), quality=q)
        if mode == "wh":
            return ResizeOptions(
                width=self.width.get(),
                height=self.height.get(),
                keep_aspect=self.keep_aspect.get(),
                quality=q,
            )
        if mode == "width":
            return ResizeOptions(width=self.width.get(), quality=q)
        return ResizeOptions(height=self.height.get(), quality=q)

    def _start(self) -> None:
        if self._busy or not self._validate_files_and_output():
            return
        self._set_busy(True)
        self.progress["value"] = 0
        self.progress["maximum"] = len(self.image_paths)
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self) -> None:
        output = self._get_output_dir()
        options = self._get_options()
        ok, fail = 0, 0
        last: Path | None = None
        for i, src in enumerate(self.image_paths, start=1):
            self.frame.after(
                0,
                lambda n=i, p=src: self.status.config(text=f"处理中 ({n}/{len(self.image_paths)}): {p.name}"),
            )
            try:
                results = process_batch_resize([src], output, options)
                last = results[0].parent
                ok += 1
            except Exception as exc:  # noqa: BLE001
                fail += 1
                self.frame.after(0, lambda m=f"失败: {src.name} ({exc})": messagebox.showwarning("错误", m))
            self.frame.after(0, lambda v=i: self.progress.configure(value=v))

        summary = f"尺寸调整完成：成功 {ok}，失败 {fail}"
        self.frame.after(0, lambda: self._on_batch_done(summary, fail, last))


class ConvertTab(FileListMixin, QualityPresetMixin):
    def __init__(self, parent: ttk.Notebook, app: ImageToolApp) -> None:
        self.app = app
        self.frame = ttk.Frame(parent)
        parent.add(self.frame, text="格式转换")

        self.image_paths: list[Path] = []
        self.recursive = tk.BooleanVar(value=False)
        self.same_dir = tk.BooleanVar(value=True)
        self.output_dir = tk.StringVar()
        self._busy = False
        self.target_format = tk.StringVar(value="JPEG (.jpg)")

        self._build_ui()

    def _build_ui(self) -> None:
        action, bottom = pack_tab_footer(self.frame)
        self.run_btn = make_action_button(action, text="开始转换", command=self._start, width=14)
        self.run_btn.pack(side=tk.LEFT)
        self._build_status_bar(bottom)

        _body, top, left = pack_file_list_tab_layout(self.frame)
        self._build_file_section(left)

        right = build_settings_panel(top, "转换设置", width=280)

        fmt_row = ttk.Frame(right)
        fmt_row.pack(fill=tk.X, padx=8, pady=4)
        ttk.Label(fmt_row, text="目标格式：", width=10).pack(side=tk.LEFT)
        fmt_combo = ttk.Combobox(
            fmt_row,
            textvariable=self.target_format,
            values=list(OUTPUT_FORMATS.keys()),
            state="readonly",
            width=14,
        )
        fmt_combo.pack(side=tk.LEFT)

        self._build_quality_controls(right, default="标准 (85)")

        ttk.Label(
            right,
            text="PNG / GIF 转 JPEG 时\n透明区域填充为白色",
            foreground="gray",
            justify=tk.LEFT,
        ).pack(anchor=tk.W, padx=8, pady=8)

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.run_btn.config(state=tk.DISABLED if busy else tk.NORMAL)

    def _get_options(self) -> ConvertOptions:
        ext = OUTPUT_FORMATS[self.target_format.get()]
        return ConvertOptions(target_ext=ext, quality=self._get_quality())

    def _start(self) -> None:
        if self._busy or not self._validate_files_and_output():
            return
        self._set_busy(True)
        self.progress["value"] = 0
        self.progress["maximum"] = len(self.image_paths)
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self) -> None:
        output = self._get_output_dir()
        options = self._get_options()
        ok, fail = 0, 0
        last: Path | None = None
        for i, src in enumerate(self.image_paths, start=1):
            self.frame.after(
                0,
                lambda n=i, p=src: self.status.config(text=f"转换中 ({n}/{len(self.image_paths)}): {p.name}"),
            )
            try:
                results = process_batch_convert([src], output, options)
                last = results[0].parent
                ok += 1
            except Exception as exc:  # noqa: BLE001
                fail += 1
                self.frame.after(0, lambda m=f"失败: {src.name} ({exc})": messagebox.showwarning("错误", m))
            self.frame.after(0, lambda v=i: self.progress.configure(value=v))

        summary = f"格式转换完成：成功 {ok}，失败 {fail}"
        self.frame.after(0, lambda: self._on_batch_done(summary, fail, last))


class CompressTab(FileListMixin, QualityPresetMixin):
    def __init__(self, parent: ttk.Notebook, app: ImageToolApp) -> None:
        self.app = app
        self.frame = ttk.Frame(parent)
        parent.add(self.frame, text="压缩")

        self.image_paths: list[Path] = []
        self.recursive = tk.BooleanVar(value=False)
        self.same_dir = tk.BooleanVar(value=True)
        self.output_dir = tk.StringVar()
        self._busy = False

        self.limit_size = tk.BooleanVar(value=False)
        self.max_side = tk.IntVar(value=1920)
        self.force_jpeg = tk.BooleanVar(value=False)

        self._build_ui()

    def _build_ui(self) -> None:
        action, bottom = pack_tab_footer(self.frame)
        self.run_btn = make_action_button(action, text="开始压缩", command=self._start, width=14)
        self.run_btn.pack(side=tk.LEFT)
        self._build_status_bar(bottom)

        body, top, left = pack_file_list_tab_layout(self.frame)
        self._build_file_section(left)

        right = build_settings_panel(top, "压缩设置", width=280)

        self._build_quality_controls(right, default="网页 (75)")

        ttk.Checkbutton(
            right,
            text="同时缩小尺寸（限制最大边长）",
            variable=self.limit_size,
        ).pack(anchor=tk.W, padx=8, pady=(8, 2))

        size_row = ttk.Frame(right)
        size_row.pack(fill=tk.X, padx=8, pady=2)
        ttk.Label(size_row, text="最大边长：", width=10).pack(side=tk.LEFT)
        ttk.Spinbox(size_row, from_=100, to=10000, textvariable=self.max_side, width=10).pack(side=tk.LEFT)

        ttk.Checkbutton(
            right,
            text="统一输出为 JPEG（体积更小）",
            variable=self.force_jpeg,
        ).pack(anchor=tk.W, padx=8, pady=8)

        ttk.Label(
            right,
            text="质量预设说明：\n原画 — 几乎无损\n网页 — 适合网站上传\n极小 — 最小文件体积",
            foreground="gray",
            justify=tk.LEFT,
        ).pack(anchor=tk.W, padx=8, pady=4)

        log_frame = ttk.LabelFrame(body, text="压缩日志")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)
        self.log = tk.Text(log_frame, height=4, state=tk.DISABLED, font=("", 11))
        self.log.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

    def _log(self, message: str) -> None:
        self.log.config(state=tk.NORMAL)
        self.log.insert(tk.END, message + "\n")
        self.log.see(tk.END)
        self.log.config(state=tk.DISABLED)

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.run_btn.config(state=tk.DISABLED if busy else tk.NORMAL)

    def _get_options(self) -> CompressOptions:
        return CompressOptions(
            quality=self._get_quality(),
            max_side=self.max_side.get() if self.limit_size.get() else None,
            force_jpeg=self.force_jpeg.get(),
        )

    def _start(self) -> None:
        if self._busy or not self._validate_files_and_output():
            return
        self.log.config(state=tk.NORMAL)
        self.log.delete("1.0", tk.END)
        self.log.config(state=tk.DISABLED)
        self._set_busy(True)
        self.progress["value"] = 0
        self.progress["maximum"] = len(self.image_paths)
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self) -> None:
        output = self._get_output_dir()
        options = self._get_options()
        ok, fail = 0, 0
        last: Path | None = None
        total_saved = 0

        for i, src in enumerate(self.image_paths, start=1):
            self.frame.after(
                0,
                lambda n=i, p=src: self.status.config(text=f"压缩中 ({n}/{len(self.image_paths)}): {p.name}"),
            )
            try:
                result = process_batch_compress([src], output, options)[0]
                last = result.path.parent
                ok += 1
                saved = result.original_bytes - result.output_bytes
                total_saved += max(0, saved)
                msg = (
                    f"{src.name}: {format_file_size(result.original_bytes)} → "
                    f"{format_file_size(result.output_bytes)} "
                    f"（节省 {result.saved_ratio:.1f}%）"
                )
                self.frame.after(0, lambda m=msg: self._log(m))
            except Exception as exc:  # noqa: BLE001
                fail += 1
                self.frame.after(0, lambda m=f"失败: {src.name} ({exc})": self._log(m))
            self.frame.after(0, lambda v=i: self.progress.configure(value=v))

        summary = f"压缩完成：成功 {ok}，失败 {fail}，共节省 {format_file_size(total_saved)}"
        self.frame.after(0, lambda: self._log(summary))
        self.frame.after(0, lambda: self._on_batch_done(summary, fail, last))


class EditTab(ttk.Frame):
    """Single-image editor with preview, rotate, flip, crop."""

    def __init__(self, parent: ttk.Notebook, app: ImageToolApp) -> None:
        super().__init__(parent)
        parent.add(self, text="编辑")
        self.app = app

        self.source_path: Path | None = None
        self.preview_image: Image.Image | None = None
        self.photo: ImageTk.PhotoImage | None = None
        self.scale = 1.0
        self.crop_start: tuple[int, int] | None = None
        self.crop_rect_id: int | None = None
        self._dirty = False

        self.angle = tk.DoubleVar(value=0.0)

        self._build_ui()

    def _build_ui(self) -> None:
        pad = {"padx": 8, "pady": 4}

        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, **pad)
        ttk.Button(toolbar, text="打开图片…", command=self._open_image).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(toolbar, text="左转 90°", command=lambda: self._rotate(-90)).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(toolbar, text="右转 90°", command=lambda: self._rotate(90)).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(toolbar, text="水平翻转", command=lambda: self._flip("horizontal")).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(toolbar, text="垂直翻转", command=lambda: self._flip("vertical")).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(toolbar, text="清除选区", command=self._clear_crop).pack(side=tk.LEFT, padx=(0, 6))

        ttk.Label(toolbar, text="自定义角度：").pack(side=tk.LEFT, padx=(12, 4))
        ttk.Spinbox(toolbar, from_=-360, to=360, textvariable=self.angle, width=6).pack(side=tk.LEFT)
        ttk.Button(toolbar, text="旋转", command=self._rotate_custom).pack(side=tk.LEFT, padx=6)

        self.status = ttk.Label(self, text="请打开一张图片")
        self.status.pack(side=tk.BOTTOM, anchor=tk.W, **pad)

        main = ttk.Frame(self)
        main.pack(fill=tk.BOTH, expand=True, **pad)

        canvas_frame = ttk.LabelFrame(main, text="预览（拖拽鼠标框选裁剪区域）")
        canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(canvas_frame, bg="#333333", cursor="crosshair")
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self.canvas.bind("<ButtonPress-1>", self._on_crop_press)
        self.canvas.bind("<B1-Motion>", self._on_crop_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_crop_release)

        side = ttk.Frame(main)
        side.pack(side=tk.RIGHT, anchor=tk.N, padx=(8, 0))

        crop_frame = ttk.LabelFrame(side, text="裁剪坐标（像素）")
        crop_frame.pack(fill=tk.X, pady=4)
        self.crop_left = tk.IntVar(value=0)
        self.crop_top = tk.IntVar(value=0)
        self.crop_right = tk.IntVar(value=100)
        self.crop_bottom = tk.IntVar(value=100)
        for label, var in [
            ("左", self.crop_left),
            ("上", self.crop_top),
            ("右", self.crop_right),
            ("下", self.crop_bottom),
        ]:
            row = ttk.Frame(crop_frame)
            row.pack(fill=tk.X, padx=8, pady=2)
            ttk.Label(row, text=f"{label}：", width=4).pack(side=tk.LEFT)
            ttk.Spinbox(row, from_=0, to=20000, textvariable=var, width=8).pack(side=tk.LEFT)

        ttk.Button(side, text="应用裁剪", command=self._apply_crop).pack(fill=tk.X, padx=8, pady=8)

        ttk.Label(
            side,
            text="旋转、翻转、裁剪仅更新预览，\n不会写入磁盘，请最后点击保存。",
            foreground="gray",
            justify=tk.LEFT,
        ).pack(anchor=tk.W, padx=8, pady=4)

        ttk.Button(side, text="保存当前图片…", command=self._save_current, width=18).pack(padx=8, pady=12)

    def _open_image(self) -> None:
        path = filedialog.askopenfilename(
            title="选择图片",
            filetypes=[("图片", "*.jpg *.jpeg *.png *.bmp *.gif *.webp *.tiff"), ("所有文件", "*.*")],
        )
        if not path:
            return
        self.source_path = Path(path)
        self.preview_image = Image.open(path)
        if self.preview_image.mode not in ("RGB", "RGBA"):
            self.preview_image = self.preview_image.convert("RGB")
        self._dirty = False
        self._update_crop_defaults()
        self._render_preview()
        self.status.config(
            text=f"已加载: {self.source_path.name} ({self.preview_image.width}×{self.preview_image.height}) — 未保存"
        )

    def _update_crop_defaults(self) -> None:
        if not self.preview_image:
            return
        w, h = self.preview_image.size
        self.crop_left.set(0)
        self.crop_top.set(0)
        self.crop_right.set(w)
        self.crop_bottom.set(h)

    def _render_preview(self) -> None:
        if not self.preview_image:
            return
        self.canvas.update_idletasks()
        cw = max(self.canvas.winfo_width(), 400)
        ch = max(self.canvas.winfo_height(), 300)
        img = self.preview_image.copy()
        ratio = min(cw / img.width, ch / img.height, 1.0)
        self.scale = ratio
        disp_w = max(1, int(img.width * ratio))
        disp_h = max(1, int(img.height * ratio))
        shown = img.resize((disp_w, disp_h), Image.Resampling.LANCZOS)
        self.photo = ImageTk.PhotoImage(shown)
        self.canvas.delete("all")
        self.canvas.config(width=disp_w, height=disp_h)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)

    def _canvas_to_image(self, x: int, y: int) -> tuple[int, int]:
        return int(x / self.scale), int(y / self.scale)

    def _on_crop_press(self, event: tk.Event) -> None:
        self.crop_start = (event.x, event.y)
        if self.crop_rect_id:
            self.canvas.delete(self.crop_rect_id)
            self.crop_rect_id = None

    def _on_crop_drag(self, event: tk.Event) -> None:
        if not self.crop_start:
            return
        if self.crop_rect_id:
            self.canvas.delete(self.crop_rect_id)
        x0, y0 = self.crop_start
        self.crop_rect_id = self.canvas.create_rectangle(x0, y0, event.x, event.y, outline="#00ff88", width=2)

    def _on_crop_release(self, event: tk.Event) -> None:
        if not self.crop_start or not self.preview_image:
            return
        x0, y0 = self.crop_start
        x1, y1 = event.x, event.y
        left, top = self._canvas_to_image(min(x0, x1), min(y0, y1))
        right, bottom = self._canvas_to_image(max(x0, x1), max(y0, y1))
        w, h = self.preview_image.size
        self.crop_left.set(max(0, left))
        self.crop_top.set(max(0, top))
        self.crop_right.set(min(w, right))
        self.crop_bottom.set(min(h, bottom))
        self.crop_start = None

    def _clear_crop(self) -> None:
        if self.crop_rect_id:
            self.canvas.delete(self.crop_rect_id)
            self.crop_rect_id = None
        self._update_crop_defaults()

        self._update_crop_defaults()

    def _mark_dirty(self, action: str) -> None:
        self._dirty = True
        w, h = self.preview_image.size if self.preview_image else (0, 0)
        self.status.config(text=f"{action} — 预览已更新 ({w}×{h})，尚未保存")

    def _rotate(self, degrees: float) -> None:
        if not self.preview_image:
            messagebox.showwarning("提示", "请先打开图片。")
            return
        self.preview_image = self.preview_image.rotate(
            degrees, expand=True, resample=Image.Resampling.BICUBIC
        )
        self._clear_crop()
        self._update_crop_defaults()
        self._render_preview()
        self._mark_dirty(f"已旋转 {degrees:g}°")

    def _rotate_custom(self) -> None:
        self._rotate(self.angle.get())

    def _flip(self, mode: str) -> None:
        if not self.preview_image:
            messagebox.showwarning("提示", "请先打开图片。")
            return
        if mode == "horizontal":
            self.preview_image = ImageOps.mirror(self.preview_image)
            label = "已水平翻转"
        else:
            self.preview_image = ImageOps.flip(self.preview_image)
            label = "已垂直翻转"
        self._clear_crop()
        self._update_crop_defaults()
        self._render_preview()
        self._mark_dirty(label)

    def _apply_crop(self) -> None:
        if not self.preview_image:
            messagebox.showwarning("提示", "请先打开图片。")
            return
        w, h = self.preview_image.size
        left = max(0, min(self.crop_left.get(), w - 1))
        top = max(0, min(self.crop_top.get(), h - 1))
        right = max(left + 1, min(self.crop_right.get(), w))
        bottom = max(top + 1, min(self.crop_bottom.get(), h))
        self.preview_image = self.preview_image.crop((left, top, right, bottom))
        self._clear_crop()
        self._update_crop_defaults()
        self._render_preview()
        self._mark_dirty("已裁剪")

    def _save_current(self) -> None:
        if not self.preview_image or not self.source_path:
            messagebox.showwarning("提示", "请先打开图片。")
            return

        src = self.source_path
        ext = src.suffix if src.suffix else ".png"
        dest = filedialog.asksaveasfilename(
            title="保存图片",
            initialdir=str(src.parent),
            initialfile=src.stem + "_edited" + ext,
            defaultextension=ext,
            filetypes=[
                ("JPEG 图片", "*.jpg *.jpeg"),
                ("PNG 图片", "*.png"),
                ("WebP 图片", "*.webp"),
                ("BMP 图片", "*.bmp"),
                ("GIF 图片", "*.gif"),
                ("TIFF 图片", "*.tiff *.tif"),
                ("所有文件", "*.*"),
            ],
        )
        if not dest:
            return
        try:
            save_image(self.preview_image, Path(dest))
            self._dirty = False
            self.source_path = Path(dest)
            self.status.config(text=f"已保存: {dest}")
            messagebox.showinfo("完成", f"已保存至\n{dest}")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("错误", str(exc))


class OcrTab(FileListMixin):
    def __init__(self, parent: ttk.Notebook, app: ImageToolApp) -> None:
        self.app = app
        self.frame = ttk.Frame(parent)
        parent.add(self.frame, text="文字识别")

        self.image_paths: list[Path] = []
        self.recursive = tk.BooleanVar(value=False)
        self.same_dir = tk.BooleanVar(value=True)
        self.output_dir = tk.StringVar()
        self._busy = False
        self.ocr_engine = tk.StringVar(value="PaddleOCR（高精度，推荐）")
        self.ocr_lang = tk.StringVar(value="chi_sim+eng")
        self.ocr_preprocess = tk.StringVar(value="自动增强（推荐）")
        self.ocr_psm = tk.StringVar(value="6 — 单块文本（文档/截图）")
        self.ocr_upscale = tk.BooleanVar(value=True)
        self.ocr_min_side = tk.IntVar(value=1600)
        self.ocr_orientation = tk.BooleanVar(value=True)
        self.ocr_doc_preprocess = tk.BooleanVar(value=False)
        self.ocr_min_score = tk.DoubleVar(value=0.5)
        self.last_text = ""

        self._build_ui()

    def _build_ui(self) -> None:
        action, bottom = pack_tab_footer(self.frame)
        self.run_btn = make_action_button(action, text="开始识别", command=self._start, width=12)
        self.run_btn.pack(side=tk.LEFT, padx=(0, 8))
        make_action_button(action, text="导出 TXT", command=self._export_txt, width=10).pack(
            side=tk.LEFT, padx=(0, 8)
        )
        make_action_button(action, text="导出 Word", command=self._export_docx, width=11).pack(side=tk.LEFT)
        self._build_ocr_status_bar(bottom)

        body = ttk.Frame(self.frame)
        body.pack(fill=tk.BOTH, expand=True)

        main_row = ttk.Frame(body)
        main_row.pack(fill=tk.BOTH, expand=True, pady=(4, 0))

        left = ttk.Frame(main_row)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, anchor=tk.N)
        self._build_file_section(left)

        right = build_settings_panel(main_row, "OCR 设置", width=280)

        ttk.Label(right, text="识别引擎：").pack(anchor=tk.W, padx=8, pady=2)
        engine_combo = ttk.Combobox(
            right,
            textvariable=self.ocr_engine,
            values=list(OCR_ENGINE_OPTIONS.keys()),
            state="readonly",
            width=22,
        )
        engine_combo.pack(padx=8, pady=2)
        engine_combo.bind("<<ComboboxSelected>>", lambda _e: self._on_engine_change())

        ttk.Label(right, text="语言包：").pack(anchor=tk.W, padx=8, pady=2)
        lang_combo = ttk.Combobox(
            right,
            textvariable=self.ocr_lang,
            values=["chi_sim+eng", "chi_sim", "eng", "chi_tra+eng", "jpn+eng"],
            state="readonly",
            width=18,
        )
        lang_combo.pack(padx=8, pady=4)
        lang_combo.bind("<<ComboboxSelected>>", lambda _e: self._refresh_env_status())

        self.paddle_frame = ttk.Frame(right)
        self.paddle_frame.pack(fill=tk.X, anchor=tk.N)
        ttk.Checkbutton(
            self.paddle_frame,
            text="文字方向自动校正",
            variable=self.ocr_orientation,
        ).pack(anchor=tk.W, padx=8, pady=2)
        ttk.Checkbutton(
            self.paddle_frame,
            text="文档矫正（拍照/曲面，较慢）",
            variable=self.ocr_doc_preprocess,
        ).pack(anchor=tk.W, padx=8, pady=2)
        score_row = ttk.Frame(self.paddle_frame)
        score_row.pack(fill=tk.X, padx=8, pady=2)
        ttk.Label(score_row, text="最低置信度：").pack(side=tk.LEFT)
        ttk.Spinbox(score_row, from_=0.0, to=1.0, increment=0.05, textvariable=self.ocr_min_score, width=6).pack(
            side=tk.LEFT
        )

        ttk.Label(right, text="图像预处理：").pack(anchor=tk.W, padx=8, pady=(8, 2))
        preprocess_combo = ttk.Combobox(
            right,
            textvariable=self.ocr_preprocess,
            values=list(OCR_PREPROCESS_OPTIONS.keys()),
            state="readonly",
            width=22,
        )
        preprocess_combo.pack(padx=8, pady=2)

        ttk.Checkbutton(
            right,
            text="自动放大小图（提高清晰度）",
            variable=self.ocr_upscale,
        ).pack(anchor=tk.W, padx=8, pady=2)

        side_row = ttk.Frame(right)
        side_row.pack(fill=tk.X, padx=8, pady=2)
        ttk.Label(side_row, text="最小边长：").pack(side=tk.LEFT)
        ttk.Spinbox(side_row, from_=800, to=4000, increment=100, textvariable=self.ocr_min_side, width=8).pack(
            side=tk.LEFT
        )

        self.tesseract_frame = ttk.Frame(right)
        self.psm_label = ttk.Label(self.tesseract_frame, text="版面模式 (PSM)：")
        self.psm_label.pack(anchor=tk.W, padx=8, pady=(8, 2))
        self.psm_combo = ttk.Combobox(
            self.tesseract_frame,
            textvariable=self.ocr_psm,
            values=list(OCR_PSM_OPTIONS.keys()),
            state="readonly",
            width=22,
        )
        self.psm_combo.pack(padx=8, pady=2)

        env_row = ttk.Frame(right)
        env_row.pack(fill=tk.X, padx=8, pady=(8, 2))
        ttk.Button(env_row, text="检测环境", command=self._refresh_env_status_detailed, width=10).pack(side=tk.LEFT)

        self.ocr_env_label = ttk.Label(right, text="", justify=tk.LEFT, wraplength=220)
        self.ocr_env_label.pack(anchor=tk.W, padx=8, pady=4)
        ttk.Label(
            right,
            text="PaddleOCR 适合中文/复杂场景；\nTesseract 需配合 PSM 使用。",
            foreground="gray",
            justify=tk.LEFT,
        ).pack(anchor=tk.W, padx=8, pady=(2, 4))

        result_frame = ttk.LabelFrame(left, text="识别结果")
        result_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        result_toolbar = ttk.Frame(result_frame)
        result_toolbar.pack(fill=tk.X, padx=8, pady=(6, 0))
        ttk.Button(result_toolbar, text="清空结果", command=self._clear_results).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(result_toolbar, text="复制结果", command=self._copy_results).pack(side=tk.LEFT)

        self.result_text = scrolledtext.ScrolledText(result_frame, height=10, font=("", 12), wrap=tk.WORD)
        self.result_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=(4, 8))

        self._on_engine_change()
        self.frame.after(200, self._refresh_env_status)

    def _build_ocr_status_bar(self, parent: ttk.Frame) -> None:
        pad = {"padx": 8, "pady": 4}
        status_row = ttk.Frame(parent)
        status_row.pack(fill=tk.X, **pad)
        self.status = ttk.Label(status_row, text="就绪")
        self.status.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.progress_pct = ttk.Label(status_row, text="0%", width=6, anchor=tk.E)
        self.progress_pct.pack(side=tk.RIGHT)

        progress_row = ttk.Frame(parent)
        progress_row.pack(fill=tk.X, **pad)
        self.progress = ttk.Progressbar(progress_row, mode="determinate", maximum=100)
        self.progress.pack(fill=tk.X)

    def _update_progress(self, percent: int, message: str) -> None:
        percent = max(0, min(100, int(percent)))
        self.progress["value"] = percent
        self.progress_pct.config(text=f"{percent}%")
        self.status.config(text=message)

    def _is_paddle_engine(self) -> bool:
        return OCR_ENGINE_OPTIONS.get(self.ocr_engine.get(), "paddle") == "paddle"

    def _on_engine_change(self) -> None:
        use_paddle = self._is_paddle_engine()
        self.paddle_frame.pack_forget()
        self.tesseract_frame.pack_forget()
        if use_paddle:
            self.paddle_frame.pack(fill=tk.X, anchor=tk.N)
        else:
            self.tesseract_frame.pack(fill=tk.X, anchor=tk.N)
        self._refresh_env_status()

    def _get_ocr_options(self) -> OcrOptions:
        preprocess = OCR_PREPROCESS_OPTIONS.get(self.ocr_preprocess.get(), "auto")
        psm = OCR_PSM_OPTIONS.get(self.ocr_psm.get(), 6)
        engine = OCR_ENGINE_OPTIONS.get(self.ocr_engine.get(), "paddle")
        return OcrOptions(
            engine=engine,  # type: ignore[arg-type]
            lang=self.ocr_lang.get(),
            preprocess=preprocess,  # type: ignore[arg-type]
            upscale=self.ocr_upscale.get(),
            min_side=self.ocr_min_side.get(),
            psm=psm,
            use_textline_orientation=self.ocr_orientation.get(),
            use_doc_preprocess=self.ocr_doc_preprocess.get(),
            min_score=self.ocr_min_score.get(),
        )

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.run_btn.config(state=tk.DISABLED if busy else tk.NORMAL)

    def _refresh_env_status(self) -> None:
        options = self._get_ocr_options()
        if options.engine == "paddle":
            from ocr_engines import check_paddle_ocr

            ready, message = check_paddle_ocr(detailed=False)
        else:
            ready, message = check_ocr_environment(options)
        self.ocr_env_label.config(text=message, foreground="#22863a" if ready else "#cb2431")

    def _refresh_env_status_detailed(self) -> None:
        options = self._get_ocr_options()
        if options.engine == "paddle":
            from ocr_engines import check_paddle_ocr

            ready, message = check_paddle_ocr(detailed=True)
        else:
            ready, message = check_ocr_environment(options)
        self.ocr_env_label.config(text=message, foreground="#22863a" if ready else "#cb2431")

    def _start(self) -> None:
        if self._busy:
            return
        if not self.image_paths:
            messagebox.showwarning("提示", "请先添加至少一张图片。")
            return
        options = self._get_ocr_options()
        ready, message = check_ocr_environment(options)
        if not ready:
            messagebox.showerror("OCR 环境未就绪", message)
            self._refresh_env_status()
            return
        self._set_busy(True)
        self._update_progress(0, "准备识别…")
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self) -> None:
        from ocr_engines import run_ocr

        options = self._get_ocr_options()
        parts: list[str] = []
        ok, fail = 0, 0
        total = len(self.image_paths)

        for i, src in enumerate(self.image_paths, start=1):
            prefix = f"[{i}/{total}] {src.name}"

            def on_progress(file_pct: int, msg: str, idx: int = i) -> None:
                overall = int(((idx - 1) + file_pct / 100.0) / total * 100)
                overall = max(0, min(99 if idx < total else 100, overall))
                detail = f"{prefix} — {msg}"
                self.frame.after(0, lambda p=overall, m=detail: self._update_progress(p, m))

            self.frame.after(
                0,
                lambda idx=i, p=src: self._update_progress(
                    int((idx - 1) / total * 100),
                    f"[{idx}/{total}] {p.name} — 开始处理…",
                ),
            )
            try:
                text = run_ocr(src, options=options, on_progress=on_progress)
                header = f"=== {src.name} ==="
                parts.append(f"{header}\n{text}\n")
                ok += 1
            except Exception as exc:  # noqa: BLE001
                fail += 1
                parts.append(f"=== {src.name} ===\n[识别失败: {exc}]\n")
            self.frame.after(
                0,
                lambda idx=i: self._update_progress(int(idx / total * 100), f"[{idx}/{total}] 已完成"),
            )

        combined = "\n".join(parts).strip()
        self.last_text = combined

        def update_ui() -> None:
            self.result_text.delete("1.0", tk.END)
            self.result_text.insert(tk.END, combined)
            self._set_busy(False)
            summary = f"识别完成：成功 {ok}，失败 {fail}"
            self._update_progress(100, summary)
            if fail:
                messagebox.showwarning("完成", summary)

        self.frame.after(0, update_ui)

    def _clear_results(self) -> None:
        self.result_text.delete("1.0", tk.END)
        self.last_text = ""
        self.status.config(text="已清空识别结果")

    def _copy_results(self) -> None:
        text = self.result_text.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning("提示", "没有可复制的内容。")
            return
        self.frame.clipboard_clear()
        self.frame.clipboard_append(text)
        self.status.config(text="识别结果已复制到剪贴板")

    def _export_txt(self) -> None:
        text = self.result_text.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning("提示", "没有可导出的文字，请先执行识别。")
            return
        path = filedialog.asksaveasfilename(
            title="保存 TXT",
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
        )
        if path:
            try:
                export_ocr_txt(text, Path(path))
                messagebox.showinfo("完成", f"已保存至 {path}")
            except Exception as exc:  # noqa: BLE001
                messagebox.showerror("错误", str(exc))

    def _export_docx(self) -> None:
        text = self.result_text.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning("提示", "没有可导出的文字，请先执行识别。")
            return
        path = filedialog.asksaveasfilename(
            title="保存 Word",
            defaultextension=".docx",
            filetypes=[("Word 文档", "*.docx"), ("所有文件", "*.*")],
        )
        if path:
            try:
                export_ocr_docx(text, Path(path))
                messagebox.showinfo("完成", f"已保存至 {path}")
            except Exception as exc:  # noqa: BLE001
                messagebox.showerror("错误", str(exc))


class ImageToolApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("图片处理工具")
        self.root.minsize(1024, 720)
        self.root.geometry("1120x820")

        notebook = ttk.Notebook(root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self.watermark_tab = WatermarkTab(notebook, self)
        self.convert_tab = ConvertTab(notebook, self)
        self.compress_tab = CompressTab(notebook, self)
        self.resize_tab = ResizeTab(notebook, self)
        self.edit_tab = EditTab(notebook, self)
        self.ocr_tab = OcrTab(notebook, self)


def configure_app_style(root: tk.Tk) -> None:
    """Avoid clipped Chinese button labels, especially on macOS aqua theme."""
    style = ttk.Style(root)
    try:
        if sys.platform == "darwin":
            style.theme_use("aqua")
    except tk.TclError:
        pass

    if sys.platform == "darwin":
        button_pad = (14, 10)
        tab_pad = (14, 8)
        default_font = ("PingFang SC", 13)
    else:
        button_pad = (12, 6)
        tab_pad = (12, 6)
        default_font = ("", 11)

    style.configure("TButton", padding=button_pad, font=default_font)
    style.configure("Action.TButton", padding=button_pad, font=default_font)
    style.configure("TNotebook.Tab", padding=tab_pad, font=default_font)


def make_action_button(parent: ttk.Frame, **kwargs) -> ttk.Button:
    """Primary/secondary buttons in bottom action bars."""
    return ttk.Button(parent, style="Action.TButton", **kwargs)


def main() -> None:
    root = tk.Tk()
    configure_app_style(root)
    ImageToolApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
