#!/usr/bin/env python3
"""PDF 转 Word 图形界面。"""

from __future__ import annotations

import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from pdf_to_word import collect_pdfs, convert_pdf, resolve_docx_path


class PdfToWordApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("PDF 转 Word")
        self.root.minsize(520, 480)
        self.root.geometry("640x560")

        self.pdf_paths: list[Path] = []
        self.output_dir = tk.StringVar()
        self.recursive = tk.BooleanVar(value=False)
        self.same_dir = tk.BooleanVar(value=True)
        self._busy = False

        self._build_ui()

    def _build_ui(self) -> None:
        pad = {"padx": 10, "pady": 4}

        # 先固定底部操作栏，避免被上方可伸缩区域挤出窗口
        action_row = ttk.Frame(self.root)
        action_row.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 10))
        self.convert_btn = ttk.Button(
            action_row,
            text="开始转换",
            command=self._start_convert,
            width=14,
        )
        self.convert_btn.pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(action_row, text="打开输出目录", command=self._open_output).pack(
            side=tk.LEFT
        )
        ttk.Label(
            action_row,
            text="添加 PDF 后点击下方按钮开始",
            foreground="gray",
        ).pack(side=tk.RIGHT)

        prog_frame = ttk.Frame(self.root)
        prog_frame.pack(side=tk.BOTTOM, fill=tk.X, **pad)
        self.status = ttk.Label(prog_frame, text="就绪 — 添加文件后点击「开始转换」")
        self.status.pack(anchor=tk.W)
        self.progress = ttk.Progressbar(prog_frame, mode="determinate")
        self.progress.pack(fill=tk.X, pady=4)

        file_frame = ttk.LabelFrame(self.root, text="待转换的 PDF")
        file_frame.pack(fill=tk.BOTH, expand=True, **pad)

        list_frame = ttk.Frame(file_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        scroll = ttk.Scrollbar(list_frame)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.file_list = tk.Listbox(
            list_frame,
            selectmode=tk.EXTENDED,
            yscrollcommand=scroll.set,
            font=("", 12),
        )
        self.file_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.config(command=self.file_list.yview)

        btn_row = ttk.Frame(file_frame)
        btn_row.pack(fill=tk.X, padx=8, pady=(0, 8))
        ttk.Button(btn_row, text="添加文件…", command=self._add_files).pack(
            side=tk.LEFT, padx=(0, 6)
        )
        ttk.Button(btn_row, text="添加文件夹…", command=self._add_folder).pack(
            side=tk.LEFT, padx=(0, 6)
        )
        ttk.Button(btn_row, text="移除选中", command=self._remove_selected).pack(
            side=tk.LEFT, padx=(0, 6)
        )
        ttk.Button(btn_row, text="清空", command=self._clear_list).pack(side=tk.LEFT)

        out_frame = ttk.LabelFrame(self.root, text="输出设置")
        out_frame.pack(fill=tk.X, **pad)

        ttk.Checkbutton(
            out_frame,
            text="输出到 PDF 同目录（默认）",
            variable=self.same_dir,
            command=self._toggle_output_dir,
        ).pack(anchor=tk.W, padx=8, pady=(8, 2))

        dir_row = ttk.Frame(out_frame)
        dir_row.pack(fill=tk.X, padx=8, pady=(2, 8))
        ttk.Label(dir_row, text="输出目录：").pack(side=tk.LEFT)
        self.output_entry = ttk.Entry(
            dir_row, textvariable=self.output_dir, state=tk.DISABLED
        )
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

        log_frame = ttk.LabelFrame(self.root, text="日志")
        log_frame.pack(fill=tk.X, **pad)
        self.log = tk.Text(log_frame, height=5, state=tk.DISABLED, font=("", 11))
        self.log.pack(fill=tk.X, padx=8, pady=8)

    def _toggle_output_dir(self) -> None:
        use_same = self.same_dir.get()
        state = tk.DISABLED if use_same else tk.NORMAL
        self.output_entry.config(state=state)
        self.browse_btn.config(state=state)
        if use_same:
            self.output_dir.set("")

    def _log(self, message: str) -> None:
        self.log.config(state=tk.NORMAL)
        self.log.insert(tk.END, message + "\n")
        self.log.see(tk.END)
        self.log.config(state=tk.DISABLED)

    def _refresh_listbox(self) -> None:
        self.file_list.delete(0, tk.END)
        for path in self.pdf_paths:
            self.file_list.insert(tk.END, str(path))
        self.status.config(text=f"已添加 {len(self.pdf_paths)} 个文件")

    def _merge_pdfs(self, new_paths: list[Path]) -> None:
        seen = {p.resolve() for p in self.pdf_paths}
        for path in new_paths:
            key = path.resolve()
            if key not in seen:
                seen.add(key)
                self.pdf_paths.append(path)
        self.pdf_paths.sort(key=lambda p: str(p).lower())
        self._refresh_listbox()

    def _add_files(self) -> None:
        paths = filedialog.askopenfilenames(
            title="选择 PDF 文件",
            filetypes=[("PDF 文件", "*.pdf"), ("所有文件", "*.*")],
        )
        if paths:
            self._merge_pdfs([Path(p) for p in paths])

    def _add_folder(self) -> None:
        folder = filedialog.askdirectory(title="选择包含 PDF 的文件夹")
        if not folder:
            return
        pdfs = collect_pdfs([Path(folder)], self.recursive.get())
        if not pdfs:
            messagebox.showinfo("提示", "该文件夹中未找到 PDF 文件。")
            return
        self._merge_pdfs(pdfs)

    def _remove_selected(self) -> None:
        indices = list(self.file_list.curselection())
        if not indices:
            return
        for i in reversed(indices):
            del self.pdf_paths[i]
        self._refresh_listbox()

    def _clear_list(self) -> None:
        self.pdf_paths.clear()
        self._refresh_listbox()
        self._log("已清空文件列表。")

    def _pick_output_dir(self) -> None:
        folder = filedialog.askdirectory(title="选择输出目录")
        if folder:
            self.output_dir.set(folder)
            self.same_dir.set(False)
            self._toggle_output_dir()

    def _get_output_path(self) -> Path | None:
        if self.same_dir.get():
            return None
        text = self.output_dir.get().strip()
        return Path(text) if text else None

    def _open_output(self) -> None:
        out = self._get_output_path()
        if out and out.is_dir():
            target = out
        elif self.pdf_paths:
            target = self.pdf_paths[0].parent
        else:
            messagebox.showinfo("提示", "请先添加文件或指定输出目录。")
            return
        self._reveal_in_finder(target)

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

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        state = tk.DISABLED if busy else tk.NORMAL
        self.convert_btn.config(state=state)

    def _start_convert(self) -> None:
        if self._busy:
            return
        if not self.pdf_paths:
            messagebox.showwarning("提示", "请先添加至少一个 PDF 文件。")
            return
        if not self.same_dir.get() and not self.output_dir.get().strip():
            messagebox.showwarning("提示", "请指定输出目录，或勾选「输出到 PDF 同目录」。")
            return

        self._set_busy(True)
        self.progress["value"] = 0
        self.progress["maximum"] = len(self.pdf_paths)
        thread = threading.Thread(target=self._run_convert, daemon=True)
        thread.start()

    def _run_convert(self) -> None:
        output = self._get_output_path()
        batch_mode = len(self.pdf_paths) > 1
        ok, fail = 0, 0
        last_output: Path | None = None

        for i, pdf in enumerate(self.pdf_paths, start=1):
            self.root.after(0, lambda n=i, p=pdf: self.status.config(text=f"正在转换 ({n}/{len(self.pdf_paths)}): {p.name}"))

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

    def _on_done(self, summary: str, fail: int, last_output: Path | None) -> None:
        self._set_busy(False)
        self.status.config(text=summary)
        self._log(summary)
        if fail:
            messagebox.showwarning("完成", summary)
        else:
            messagebox.showinfo("完成", summary)
            if last_output and messagebox.askyesno("打开目录", "是否在文件管理器中打开输出目录？"):
                self._reveal_in_finder(last_output)


def main() -> None:
    root = tk.Tk()
    try:
        style = ttk.Style()
        if sys.platform == "darwin":
            style.theme_use("aqua")
    except tk.TclError:
        pass
    PdfToWordApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
