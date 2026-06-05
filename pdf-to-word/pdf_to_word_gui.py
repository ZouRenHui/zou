#!/usr/bin/env python3
"""PDF 工具箱图形界面：转 Word、拼接、拆分。"""

from __future__ import annotations

import subprocess
from collections.abc import Callable
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from pdf_to_word import collect_pdfs, convert_pdf, resolve_docx_path
from pdf_tools import merge_pdfs, split_pdf_by_ranges, split_pdf_each_page


class PdfToolboxApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("PDF 工具箱")
        self.root.minsize(560, 520)
        self.root.geometry("700x620")

        self._busy = False
        self._last_output_dir: Path | None = None

        # Tab: 转 Word
        self.convert_paths: list[Path] = []
        self.convert_output_dir = tk.StringVar()
        self.convert_same_dir = tk.BooleanVar(value=True)
        self.convert_recursive = tk.BooleanVar(value=False)

        # Tab: 拼接
        self.merge_paths: list[Path] = []
        self.merge_output = tk.StringVar()

        # Tab: 拆分
        self.split_input = tk.StringVar()
        self.split_output_dir = tk.StringVar()
        self.split_mode = tk.StringVar(value="each")
        self.split_ranges = tk.StringVar(value="1-1")

        self._build_shell()
        self._build_convert_tab()
        self._build_merge_tab()
        self._build_split_tab()
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)
        self._on_tab_changed()

    # ------------------------------------------------------------------ UI shell
    def _build_shell(self) -> None:
        pad = {"padx": 10, "pady": 4}

        action_row = ttk.Frame(self.root)
        action_row.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 10))
        self.action_btn = ttk.Button(action_row, text="执行", command=self._run_action, width=14)
        self.action_btn.pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(action_row, text="打开输出目录", command=self._open_output).pack(side=tk.LEFT)
        self.action_hint = ttk.Label(action_row, text="", foreground="gray")
        self.action_hint.pack(side=tk.RIGHT)

        prog_frame = ttk.Frame(self.root)
        prog_frame.pack(side=tk.BOTTOM, fill=tk.X, **pad)
        self.status = ttk.Label(prog_frame, text="就绪")
        self.status.pack(anchor=tk.W)
        self.progress = ttk.Progressbar(prog_frame, mode="determinate")
        self.progress.pack(fill=tk.X, pady=4)

        log_frame = ttk.LabelFrame(self.root, text="日志")
        log_frame.pack(side=tk.BOTTOM, fill=tk.X, **pad)
        self.log = tk.Text(log_frame, height=5, state=tk.DISABLED, font=("", 11))
        self.log.pack(fill=tk.X, padx=8, pady=8)

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 0))

        self.tab_convert = ttk.Frame(self.notebook)
        self.tab_merge = ttk.Frame(self.notebook)
        self.tab_split = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_convert, text="PDF 转 Word")
        self.notebook.add(self.tab_merge, text="拼接 PDF")
        self.notebook.add(self.tab_split, text="拆分 PDF")

    def _build_list_panel(
        self,
        parent: ttk.Frame,
        *,
        on_add_files,
        on_add_folder=None,
        on_remove,
        on_clear,
        extra_buttons: list[tuple[str, Callable[[], None]]] | None = None,
    ) -> tk.Listbox:
        list_frame = ttk.Frame(parent)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        scroll = ttk.Scrollbar(list_frame)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        listbox = tk.Listbox(list_frame, selectmode=tk.EXTENDED, yscrollcommand=scroll.set, font=("", 12))
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.config(command=listbox.yview)

        btn_row = ttk.Frame(parent)
        btn_row.pack(fill=tk.X, padx=8, pady=(0, 8))
        ttk.Button(btn_row, text="添加文件…", command=on_add_files).pack(side=tk.LEFT, padx=(0, 6))
        if on_add_folder:
            ttk.Button(btn_row, text="添加文件夹…", command=on_add_folder).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_row, text="移除选中", command=on_remove).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_row, text="清空", command=on_clear).pack(side=tk.LEFT, padx=(0, 6))
        if extra_buttons:
            for text, cmd in extra_buttons:
                ttk.Button(btn_row, text=text, command=cmd).pack(side=tk.LEFT, padx=(0, 6))
        return listbox

    # ------------------------------------------------------------------ Tab: convert
    def _build_convert_tab(self) -> None:
        file_frame = ttk.LabelFrame(self.tab_convert, text="待转换的 PDF")
        file_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)
        self.convert_list = self._build_list_panel(
            file_frame,
            on_add_files=self._convert_add_files,
            on_add_folder=self._convert_add_folder,
            on_remove=self._convert_remove,
            on_clear=self._convert_clear,
        )

        out_frame = ttk.LabelFrame(self.tab_convert, text="输出设置")
        out_frame.pack(fill=tk.X, padx=10, pady=(0, 8))
        ttk.Checkbutton(
            out_frame,
            text="输出到 PDF 同目录（默认）",
            variable=self.convert_same_dir,
            command=self._convert_toggle_output_dir,
        ).pack(anchor=tk.W, padx=8, pady=(8, 2))

        dir_row = ttk.Frame(out_frame)
        dir_row.pack(fill=tk.X, padx=8, pady=(2, 8))
        ttk.Label(dir_row, text="输出目录：").pack(side=tk.LEFT)
        self.convert_output_entry = ttk.Entry(
            dir_row, textvariable=self.convert_output_dir, state=tk.DISABLED
        )
        self.convert_output_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)
        self.convert_browse_btn = ttk.Button(
            dir_row, text="浏览…", command=self._convert_pick_output_dir, state=tk.DISABLED
        )
        self.convert_browse_btn.pack(side=tk.LEFT)

        ttk.Checkbutton(
            out_frame,
            text="添加文件夹时递归扫描子目录",
            variable=self.convert_recursive,
        ).pack(anchor=tk.W, padx=8, pady=(0, 8))

    # ------------------------------------------------------------------ Tab: merge
    def _build_merge_tab(self) -> None:
        file_frame = ttk.LabelFrame(self.tab_merge, text="待拼接的 PDF（按列表顺序拼接）")
        file_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)
        self.merge_list = self._build_list_panel(
            file_frame,
            on_add_files=self._merge_add_files,
            on_remove=self._merge_remove,
            on_clear=self._merge_clear,
            extra_buttons=[
                ("上移", self._merge_move_up),
                ("下移", self._merge_move_down),
            ],
        )

        out_frame = ttk.LabelFrame(self.tab_merge, text="输出文件")
        out_frame.pack(fill=tk.X, padx=10, pady=(0, 8))
        row = ttk.Frame(out_frame)
        row.pack(fill=tk.X, padx=8, pady=8)
        ttk.Label(row, text="保存为：").pack(side=tk.LEFT)
        ttk.Entry(row, textvariable=self.merge_output).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)
        ttk.Button(row, text="浏览…", command=self._merge_pick_output).pack(side=tk.LEFT)

    # ------------------------------------------------------------------ Tab: split
    def _build_split_tab(self) -> None:
        src_frame = ttk.LabelFrame(self.tab_split, text="待拆分的 PDF")
        src_frame.pack(fill=tk.X, padx=10, pady=8)
        row = ttk.Frame(src_frame)
        row.pack(fill=tk.X, padx=8, pady=8)
        ttk.Entry(row, textvariable=self.split_input).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        ttk.Button(row, text="选择文件…", command=self._split_pick_input).pack(side=tk.LEFT)

        mode_frame = ttk.LabelFrame(self.tab_split, text="拆分方式")
        mode_frame.pack(fill=tk.X, padx=10, pady=(0, 8))
        ttk.Radiobutton(
            mode_frame,
            text="每页单独拆分（生成多个单页 PDF）",
            variable=self.split_mode,
            value="each",
        ).pack(anchor=tk.W, padx=8, pady=(8, 2))
        range_row = ttk.Frame(mode_frame)
        range_row.pack(fill=tk.X, padx=8, pady=(2, 8))
        ttk.Radiobutton(
            range_row,
            text="按页码范围拆分：",
            variable=self.split_mode,
            value="ranges",
        ).pack(side=tk.LEFT)
        ttk.Entry(range_row, textvariable=self.split_ranges, width=28).pack(side=tk.LEFT, padx=6)
        ttk.Label(
            mode_frame,
            text="示例：1-3, 5, 7-10（页码从 1 开始）",
            foreground="gray",
        ).pack(anchor=tk.W, padx=8, pady=(0, 8))

        out_frame = ttk.LabelFrame(self.tab_split, text="输出目录")
        out_frame.pack(fill=tk.X, padx=10, pady=(0, 8))
        row2 = ttk.Frame(out_frame)
        row2.pack(fill=tk.X, padx=8, pady=8)
        ttk.Entry(row2, textvariable=self.split_output_dir).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        ttk.Button(row2, text="浏览…", command=self._split_pick_output_dir).pack(side=tk.LEFT)

    # ------------------------------------------------------------------ helpers
    def _log(self, message: str) -> None:
        self.log.config(state=tk.NORMAL)
        self.log.insert(tk.END, message + "\n")
        self.log.see(tk.END)
        self.log.config(state=tk.DISABLED)

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.action_btn.config(state=tk.DISABLED if busy else tk.NORMAL)

    def _on_tab_changed(self, _event=None) -> None:
        idx = self.notebook.index(self.notebook.select())
        labels = [
            ("开始转换", "添加 PDF 后点击开始转换"),
            ("开始拼接", "按顺序添加 PDF 并指定输出文件名"),
            ("开始拆分", "选择 PDF 并设置拆分方式"),
        ]
        text, hint = labels[idx]
        self.action_btn.config(text=text)
        self.action_hint.config(text=hint)

    def _run_action(self) -> None:
        if self._busy:
            return
        idx = self.notebook.index(self.notebook.select())
        if idx == 0:
            self._start_convert()
        elif idx == 1:
            self._start_merge()
        else:
            self._start_split()

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

    def _open_output(self) -> None:
        if self._last_output_dir and self._last_output_dir.is_dir():
            self._reveal_in_finder(self._last_output_dir)
            return
        messagebox.showinfo("提示", "请先完成一次操作以确定输出目录。")

    def _on_done(self, summary: str, fail: int, last_output: Path | None) -> None:
        self._set_busy(False)
        self.status.config(text=summary)
        self._log(summary)
        if last_output:
            self._last_output_dir = last_output if last_output.is_dir() else last_output.parent
        if fail:
            messagebox.showwarning("完成", summary)
        else:
            messagebox.showinfo("完成", summary)
            if self._last_output_dir and messagebox.askyesno("打开目录", "是否在文件管理器中打开输出目录？"):
                self._reveal_in_finder(self._last_output_dir)

    def _refresh_listbox(self, listbox: tk.Listbox, paths: list[Path], status: str) -> None:
        listbox.delete(0, tk.END)
        for path in paths:
            listbox.insert(tk.END, str(path))
        self.status.config(text=status)

    def _add_unique_paths(self, paths: list[Path], existing: list[Path]) -> list[Path]:
        seen = {p.resolve() for p in existing}
        merged = list(existing)
        for path in paths:
            key = path.resolve()
            if key not in seen:
                seen.add(key)
                merged.append(path)
        return merged

    # ------------------------------------------------------------------ convert tab
    def _convert_toggle_output_dir(self) -> None:
        use_same = self.convert_same_dir.get()
        state = tk.DISABLED if use_same else tk.NORMAL
        self.convert_output_entry.config(state=state)
        self.convert_browse_btn.config(state=state)
        if use_same:
            self.convert_output_dir.set("")

    def _convert_add_files(self) -> None:
        paths = filedialog.askopenfilenames(title="选择 PDF 文件", filetypes=[("PDF 文件", "*.pdf")])
        if paths:
            self.convert_paths = self._add_unique_paths([Path(p) for p in paths], self.convert_paths)
            self.convert_paths.sort(key=lambda p: str(p).lower())
            self._refresh_listbox(self.convert_list, self.convert_paths, f"已添加 {len(self.convert_paths)} 个文件")

    def _convert_add_folder(self) -> None:
        folder = filedialog.askdirectory(title="选择包含 PDF 的文件夹")
        if not folder:
            return
        pdfs = collect_pdfs([Path(folder)], self.convert_recursive.get())
        if not pdfs:
            messagebox.showinfo("提示", "该文件夹中未找到 PDF 文件。")
            return
        self.convert_paths = self._add_unique_paths(pdfs, self.convert_paths)
        self.convert_paths.sort(key=lambda p: str(p).lower())
        self._refresh_listbox(self.convert_list, self.convert_paths, f"已添加 {len(self.convert_paths)} 个文件")

    def _convert_remove(self) -> None:
        indices = list(self.convert_list.curselection())
        for i in reversed(indices):
            del self.convert_paths[i]
        self._refresh_listbox(self.convert_list, self.convert_paths, f"已添加 {len(self.convert_paths)} 个文件")

    def _convert_clear(self) -> None:
        self.convert_paths.clear()
        self._refresh_listbox(self.convert_list, self.convert_paths, "列表已清空")

    def _convert_pick_output_dir(self) -> None:
        folder = filedialog.askdirectory(title="选择输出目录")
        if folder:
            self.convert_output_dir.set(folder)
            self.convert_same_dir.set(False)
            self._convert_toggle_output_dir()

    def _convert_get_output_path(self) -> Path | None:
        if self.convert_same_dir.get():
            return None
        text = self.convert_output_dir.get().strip()
        return Path(text) if text else None

    def _start_convert(self) -> None:
        if not self.convert_paths:
            messagebox.showwarning("提示", "请先添加至少一个 PDF 文件。")
            return
        if not self.convert_same_dir.get() and not self.convert_output_dir.get().strip():
            messagebox.showwarning("提示", "请指定输出目录，或勾选「输出到 PDF 同目录」。")
            return

        self._set_busy(True)
        self.progress["value"] = 0
        self.progress["maximum"] = len(self.convert_paths)
        threading.Thread(target=self._run_convert, daemon=True).start()

    def _run_convert(self) -> None:
        output = self._convert_get_output_path()
        batch_mode = len(self.convert_paths) > 1
        ok, fail = 0, 0
        last_output: Path | None = None

        for i, pdf in enumerate(self.convert_paths, start=1):
            self.root.after(
                0,
                lambda n=i, p=pdf: self.status.config(
                    text=f"正在转换 ({n}/{len(self.convert_paths)}): {p.name}"
                ),
            )
            try:
                docx = resolve_docx_path(pdf, output, batch_mode=batch_mode)
                result = convert_pdf(pdf, docx)
                last_output = result.parent
                ok += 1
                self.root.after(0, lambda m=f"完成: {pdf.name} -> {result.name}": self._log(m))
            except Exception as exc:  # noqa: BLE001
                fail += 1
                self.root.after(0, lambda m=f"失败: {pdf.name} ({exc})": self._log(m))
            self.root.after(0, lambda v=i: self.progress.configure(value=v))

        summary = f"转换结束：成功 {ok}，失败 {fail}"
        self.root.after(0, lambda: self._on_done(summary, fail, last_output))

    # ------------------------------------------------------------------ merge tab
    def _merge_add_files(self) -> None:
        paths = filedialog.askopenfilenames(title="选择要拼接的 PDF", filetypes=[("PDF 文件", "*.pdf")])
        if paths:
            self.merge_paths = self._add_unique_paths([Path(p) for p in paths], self.merge_paths)
            self._refresh_listbox(self.merge_list, self.merge_paths, f"已添加 {len(self.merge_paths)} 个文件")
            if not self.merge_output.get().strip() and self.merge_paths:
                self.merge_output.set(str(self.merge_paths[0].parent / "合并结果.pdf"))

    def _merge_remove(self) -> None:
        indices = list(self.merge_list.curselection())
        for i in reversed(indices):
            del self.merge_paths[i]
        self._refresh_listbox(self.merge_list, self.merge_paths, f"已添加 {len(self.merge_paths)} 个文件")

    def _merge_clear(self) -> None:
        self.merge_paths.clear()
        self._refresh_listbox(self.merge_list, self.merge_paths, "列表已清空")

    def _merge_move_up(self) -> None:
        indices = list(self.merge_list.curselection())
        if not indices or indices[0] == 0:
            return
        for i in indices:
            self.merge_paths[i - 1], self.merge_paths[i] = self.merge_paths[i], self.merge_paths[i - 1]
        self._refresh_listbox(self.merge_list, self.merge_paths, "已调整拼接顺序")
        for i in indices:
            self.merge_list.selection_set(i - 1)

    def _merge_move_down(self) -> None:
        indices = list(self.merge_list.curselection())
        if not indices or indices[-1] == len(self.merge_paths) - 1:
            return
        for i in reversed(indices):
            self.merge_paths[i + 1], self.merge_paths[i] = self.merge_paths[i], self.merge_paths[i + 1]
        self._refresh_listbox(self.merge_list, self.merge_paths, "已调整拼接顺序")
        for i in indices:
            self.merge_list.selection_set(i + 1)

    def _merge_pick_output(self) -> None:
        path = filedialog.asksaveasfilename(
            title="保存拼接后的 PDF",
            defaultextension=".pdf",
            filetypes=[("PDF 文件", "*.pdf")],
            initialfile="合并结果.pdf",
        )
        if path:
            self.merge_output.set(path)

    def _start_merge(self) -> None:
        if len(self.merge_paths) < 2:
            messagebox.showwarning("提示", "拼接至少需要 2 个 PDF 文件。")
            return
        out_text = self.merge_output.get().strip()
        if not out_text:
            messagebox.showwarning("提示", "请指定输出 PDF 文件名。")
            return
        output = Path(out_text)
        if output.suffix.lower() != ".pdf":
            output = output.with_suffix(".pdf")

        self._set_busy(True)
        self.progress["mode"] = "indeterminate"
        self.progress.start(10)
        threading.Thread(target=self._run_merge, args=(output,), daemon=True).start()

    def _run_merge(self, output: Path) -> None:
        self.root.after(0, lambda: self.status.config(text="正在拼接 PDF..."))
        try:
            result = merge_pdfs(self.merge_paths, output)
            summary = f"拼接完成: {result}"
            self.root.after(0, lambda: self._log(f"完成: {' + '.join(p.name for p in self.merge_paths)} -> {result.name}"))
            self.root.after(0, lambda: self._finish_indeterminate(summary, 0, result.parent))
        except Exception as exc:  # noqa: BLE001
            self.root.after(0, lambda: self._finish_indeterminate(f"拼接失败: {exc}", 1, None))

    # ------------------------------------------------------------------ split tab
    def _split_pick_input(self) -> None:
        path = filedialog.askopenfilename(title="选择要拆分的 PDF", filetypes=[("PDF 文件", "*.pdf")])
        if path:
            self.split_input.set(path)
            if not self.split_output_dir.get().strip():
                self.split_output_dir.set(str(Path(path).parent))

    def _split_pick_output_dir(self) -> None:
        folder = filedialog.askdirectory(title="选择输出目录")
        if folder:
            self.split_output_dir.set(folder)

    def _start_split(self) -> None:
        input_text = self.split_input.get().strip()
        if not input_text:
            messagebox.showwarning("提示", "请选择要拆分的 PDF 文件。")
            return
        out_text = self.split_output_dir.get().strip()
        if not out_text:
            messagebox.showwarning("提示", "请指定输出目录。")
            return

        input_path = Path(input_text)
        output_dir = Path(out_text)
        mode = self.split_mode.get()
        ranges = self.split_ranges.get().strip()

        if mode == "ranges" and not ranges:
            messagebox.showwarning("提示", "请输入页码范围，例如：1-3, 5, 7-10")
            return

        self._set_busy(True)
        self.progress["mode"] = "indeterminate"
        self.progress.start(10)
        threading.Thread(
            target=self._run_split,
            args=(input_path, output_dir, mode, ranges),
            daemon=True,
        ).start()

    def _run_split(self, input_path: Path, output_dir: Path, mode: str, ranges: str) -> None:
        self.root.after(0, lambda: self.status.config(text=f"正在拆分: {input_path.name}"))
        try:
            if mode == "each":
                results = split_pdf_each_page(input_path, output_dir)
            else:
                results = split_pdf_by_ranges(input_path, output_dir, ranges)
            summary = f"拆分完成：生成 {len(results)} 个文件"
            for r in results:
                self.root.after(0, lambda m=f"  -> {r.name}": self._log(m))
            self.root.after(0, lambda: self._log(summary))
            self.root.after(0, lambda: self._finish_indeterminate(summary, 0, output_dir))
        except Exception as exc:  # noqa: BLE001
            self.root.after(0, lambda: self._finish_indeterminate(f"拆分失败: {exc}", 1, None))

    def _finish_indeterminate(self, summary: str, fail: int, last_output: Path | None) -> None:
        self.progress.stop()
        self.progress["mode"] = "determinate"
        self.progress["value"] = 0
        self._on_done(summary, fail, last_output)


def main() -> None:
    root = tk.Tk()
    try:
        style = ttk.Style()
        if sys.platform == "darwin":
            style.theme_use("aqua")
    except tk.TclError:
        pass
    PdfToolboxApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
