#!/usr/bin/env python3
"""语音工具箱：语音转文字、文字转语音。"""

from __future__ import annotations

import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from document_text import SUPPORTED_SUFFIXES, extract_text
from export_text import export_docx, export_txt
from synthesize import list_voices, synthesize_speech
from transcribe import WHISPER_MODELS, ffmpeg_available, transcribe_media

MEDIA_FILETYPES = [
    ("音视频文件", "*.mp3 *.wav *.m4a *.aac *.flac *.ogg *.wma *.mp4 *.mov *.avi *.mkv *.webm"),
    ("音频", "*.mp3 *.wav *.m4a *.aac *.flac *.ogg *.wma"),
    ("视频", "*.mp4 *.mov *.avi *.mkv *.webm *.wmv *.flv *.m4v"),
    ("所有文件", "*.*"),
]

DOC_FILETYPES = [
    ("文档", "*.txt *.md *.docx *.pdf *.pptx *.doc *.ppt *.rtf"),
    ("Word", "*.docx *.doc"),
    ("PDF", "*.pdf"),
    ("PowerPoint", "*.pptx *.ppt"),
    ("文本", "*.txt *.md"),
    ("所有文件", "*.*"),
]


class SpeechToolboxApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("语音工具箱")
        self.root.minsize(680, 560)
        self.root.geometry("820x680")

        self._busy = False
        self._last_output_dir: Path | None = None
        self._stt_source: Path | None = None
        self._stt_text = ""
        self._tts_source: Path | None = None
        self._tts_text = ""

        self.stt_path = tk.StringVar()
        self.stt_model = tk.StringVar(value="base")
        self.stt_language = tk.StringVar(value="自动")
        self.tts_path = tk.StringVar()
        self.tts_voice = tk.StringVar()
        self.tts_rate = tk.StringVar(value="+0%")
        self.tts_output = tk.StringVar()

        voices = list_voices()
        if voices:
            self.tts_voice.set(voices[0].voice_id)

        self._build_shell()
        self._build_stt_tab()
        self._build_tts_tab()
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)
        self._on_tab_changed()

    def _build_shell(self) -> None:
        pad = {"padx": 10, "pady": 4}

        action_row = ttk.Frame(self.root)
        action_row.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 10))
        self.action_btn = ttk.Button(action_row, text="开始识别", command=self._run_action, width=14)
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

        self.tab_stt = ttk.Frame(self.notebook)
        self.tab_tts = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_stt, text="语音转文字")
        self.notebook.add(self.tab_tts, text="文字转语音")

    def _build_stt_tab(self) -> None:
        pad = {"padx": 10, "pady": 6}

        file_frame = ttk.LabelFrame(self.tab_stt, text="选择音频 / 视频")
        file_frame.pack(fill=tk.X, **pad)
        row = ttk.Frame(file_frame)
        row.pack(fill=tk.X, padx=8, pady=8)
        ttk.Entry(row, textvariable=self.stt_path).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        ttk.Button(row, text="浏览…", command=self._pick_stt_file).pack(side=tk.LEFT)

        opt_frame = ttk.LabelFrame(self.tab_stt, text="识别设置")
        opt_frame.pack(fill=tk.X, **pad)

        model_row = ttk.Frame(opt_frame)
        model_row.pack(fill=tk.X, padx=8, pady=(8, 4))
        ttk.Label(model_row, text="模型：", width=8).pack(side=tk.LEFT)
        ttk.Combobox(
            model_row,
            textvariable=self.stt_model,
            values=list(WHISPER_MODELS),
            state="readonly",
            width=12,
        ).pack(side=tk.LEFT, padx=(0, 16))
        ttk.Label(model_row, text="语言：").pack(side=tk.LEFT)
        ttk.Combobox(
            model_row,
            textvariable=self.stt_language,
            values=["自动", "中文", "英文"],
            state="readonly",
            width=10,
        ).pack(side=tk.LEFT)

        ffmpeg_note = "已检测到 ffmpeg，可处理视频文件。" if ffmpeg_available() else (
            "未检测到 ffmpeg：仅支持常见音频；视频需安装 ffmpeg。"
        )
        ttk.Label(opt_frame, text=ffmpeg_note, foreground="gray").pack(anchor=tk.W, padx=8, pady=(0, 8))

        preview_frame = ttk.LabelFrame(self.tab_stt, text="识别结果预览")
        preview_frame.pack(fill=tk.BOTH, expand=True, **pad)

        preview_toolbar = ttk.Frame(preview_frame)
        preview_toolbar.pack(fill=tk.X, padx=8, pady=(8, 4))
        ttk.Button(preview_toolbar, text="保存为 TXT", command=self._save_stt_txt).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(preview_toolbar, text="保存为 Word", command=self._save_stt_docx).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(preview_toolbar, text="清空预览", command=self._clear_stt_preview).pack(side=tk.LEFT)

        text_frame = ttk.Frame(preview_frame)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        scroll = ttk.Scrollbar(text_frame)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.stt_preview = tk.Text(text_frame, wrap=tk.WORD, font=("", 13), yscrollcommand=scroll.set)
        self.stt_preview.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.config(command=self.stt_preview.yview)

    def _build_tts_tab(self) -> None:
        pad = {"padx": 10, "pady": 6}

        file_frame = ttk.LabelFrame(self.tab_tts, text="选择文档")
        file_frame.pack(fill=tk.X, **pad)
        row = ttk.Frame(file_frame)
        row.pack(fill=tk.X, padx=8, pady=8)
        ttk.Entry(row, textvariable=self.tts_path).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        ttk.Button(row, text="浏览…", command=self._pick_tts_file).pack(side=tk.LEFT)

        opt_frame = ttk.LabelFrame(self.tab_tts, text="合成设置")
        opt_frame.pack(fill=tk.X, **pad)

        voice_row = ttk.Frame(opt_frame)
        voice_row.pack(fill=tk.X, padx=8, pady=(8, 4))
        ttk.Label(voice_row, text="发音人：", width=8).pack(side=tk.LEFT)
        voice_labels = [v.label for v in list_voices()]
        voice_map = {v.label: v.voice_id for v in list_voices()}
        self._voice_map = voice_map
        self._voice_label = tk.StringVar(value=voice_labels[0] if voice_labels else "")
        voice_combo = ttk.Combobox(
            voice_row,
            textvariable=self._voice_label,
            values=voice_labels,
            state="readonly",
            width=28,
        )
        voice_combo.pack(side=tk.LEFT, padx=(0, 16))
        voice_combo.bind("<<ComboboxSelected>>", self._on_voice_selected)

        rate_row = ttk.Frame(opt_frame)
        rate_row.pack(fill=tk.X, padx=8, pady=(0, 8))
        ttk.Label(rate_row, text="语速：", width=8).pack(side=tk.LEFT)
        ttk.Combobox(
            rate_row,
            textvariable=self.tts_rate,
            values=["-30%", "-15%", "+0%", "+15%", "+30%"],
            state="readonly",
            width=10,
        ).pack(side=tk.LEFT)

        out_row = ttk.Frame(opt_frame)
        out_row.pack(fill=tk.X, padx=8, pady=(0, 8))
        ttk.Label(out_row, text="输出音频：", width=8).pack(side=tk.LEFT)
        ttk.Entry(out_row, textvariable=self.tts_output).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)
        ttk.Button(out_row, text="浏览…", command=self._pick_tts_output).pack(side=tk.LEFT)

        preview_frame = ttk.LabelFrame(self.tab_tts, text="文档内容预览")
        preview_frame.pack(fill=tk.BOTH, expand=True, **pad)

        preview_toolbar = ttk.Frame(preview_frame)
        preview_toolbar.pack(fill=tk.X, padx=8, pady=(8, 4))
        ttk.Button(preview_toolbar, text="提取文字", command=self._extract_tts_text).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(preview_toolbar, text="播放音频", command=self._play_tts_audio).pack(side=tk.LEFT)

        text_frame = ttk.Frame(preview_frame)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        scroll = ttk.Scrollbar(text_frame)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tts_preview = tk.Text(text_frame, wrap=tk.WORD, font=("", 13), yscrollcommand=scroll.set)
        self.tts_preview.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.config(command=self.tts_preview.yview)

        hint = (
            f"支持 {', '.join(sorted(SUPPORTED_SUFFIXES))}；"
            "文字转语音需要联网（使用 Microsoft Edge 语音服务）。"
        )
        ttk.Label(self.tab_tts, text=hint, foreground="gray", wraplength=760).pack(anchor=tk.W, padx=10, pady=(0, 8))

    def _on_voice_selected(self, _event=None) -> None:
        label = self._voice_label.get()
        voice_id = self._voice_map.get(label)
        if voice_id:
            self.tts_voice.set(voice_id)

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
        if idx == 0:
            self.action_btn.config(text="开始识别")
            self.action_hint.config(text="上传音频或视频后点击开始识别")
        else:
            self.action_btn.config(text="生成语音")
            self.action_hint.config(text="上传文档并提取文字后点击生成语音")

    def _run_action(self) -> None:
        if self._busy:
            return
        idx = self.notebook.index(self.notebook.select())
        if idx == 0:
            self._start_stt()
        else:
            self._start_tts()

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

    def _start_indeterminate(self) -> None:
        self.progress.config(mode="indeterminate")
        self.progress.start(10)

    def _stop_indeterminate(self) -> None:
        self.progress.stop()
        self.progress.config(mode="determinate", value=0)

    def _finish(self, summary: str, *, fail: int = 0, output: Path | None = None) -> None:
        self._stop_indeterminate()
        self._set_busy(False)
        self.status.config(text=summary)
        self._log(summary)
        if output:
            self._last_output_dir = output if output.is_dir() else output.parent
        if fail:
            messagebox.showwarning("完成", summary)
        elif output:
            messagebox.showinfo("完成", summary)

    def _finish_error(self, message: str) -> None:
        self._finish(message, fail=1)

    def _set_preview_text(self, widget: tk.Text, text: str) -> None:
        widget.config(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, text)
        widget.config(state=tk.NORMAL)

    def _get_preview_text(self, widget: tk.Text) -> str:
        return widget.get("1.0", tk.END).strip()

    # ------------------------------------------------------------------ STT
    def _pick_stt_file(self) -> None:
        path = filedialog.askopenfilename(title="选择音频或视频文件", filetypes=MEDIA_FILETYPES)
        if path:
            self.stt_path.set(path)
            self._stt_source = Path(path)

    def _stt_language_code(self) -> str | None:
        mapping = {"自动": None, "中文": "zh", "英文": "en"}
        return mapping.get(self.stt_language.get(), None)

    def _start_stt(self) -> None:
        text = self.stt_path.get().strip()
        if not text:
            messagebox.showwarning("提示", "请先选择音频或视频文件。")
            return
        path = Path(text)
        if not path.is_file():
            messagebox.showwarning("提示", f"文件不存在：{path}")
            return

        self._stt_source = path
        self._set_busy(True)
        self._start_indeterminate()
        threading.Thread(
            target=self._run_stt,
            args=(path, self.stt_model.get(), self._stt_language_code()),
            daemon=True,
        ).start()

    def _run_stt(self, path: Path, model: str, language: str | None) -> None:
        self.root.after(0, lambda: self.status.config(text="正在识别语音…"))

        def on_progress(message: str) -> None:
            self.root.after(0, lambda: self.status.config(text=message))
            self.root.after(0, lambda: self._log(message))

        try:
            result = transcribe_media(path, model=model, language=language, progress_callback=on_progress)
            self._stt_text = result.text
            lang = result.language or "未知"
            summary = f"识别完成：{len(result.segments)} 段，检测语言 {lang}"
            self.root.after(0, lambda: self._set_preview_text(self.stt_preview, result.text))
            self.root.after(0, lambda: self._finish(summary))
        except Exception as exc:  # noqa: BLE001
            self.root.after(0, lambda: self._finish_error(f"识别失败: {exc}"))

    def _clear_stt_preview(self) -> None:
        self._stt_text = ""
        self._set_preview_text(self.stt_preview, "")

    def _save_stt_txt(self) -> None:
        text = self._get_preview_text(self.stt_preview)
        if not text:
            messagebox.showwarning("提示", "没有可保存的识别结果。")
            return
        default_name = (self._stt_source.stem if self._stt_source else "识别结果") + ".txt"
        path = filedialog.asksaveasfilename(
            title="保存为 TXT",
            defaultextension=".txt",
            initialfile=default_name,
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
        )
        if not path:
            return
        try:
            dest = export_txt(text, Path(path))
            self._last_output_dir = dest.parent
            messagebox.showinfo("完成", f"已保存：{dest}")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("错误", str(exc))

    def _save_stt_docx(self) -> None:
        text = self._get_preview_text(self.stt_preview)
        if not text:
            messagebox.showwarning("提示", "没有可保存的识别结果。")
            return
        default_name = (self._stt_source.stem if self._stt_source else "识别结果") + ".docx"
        path = filedialog.asksaveasfilename(
            title="保存为 Word",
            defaultextension=".docx",
            initialfile=default_name,
            filetypes=[("Word 文档", "*.docx"), ("所有文件", "*.*")],
        )
        if not path:
            return
        title = self._stt_source.name if self._stt_source else "语音识别结果"
        try:
            dest = export_docx(text, Path(path), title=title)
            self._last_output_dir = dest.parent
            messagebox.showinfo("完成", f"已保存：{dest}")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("错误", str(exc))

    # ------------------------------------------------------------------ TTS
    def _pick_tts_file(self) -> None:
        path = filedialog.askopenfilename(title="选择文档", filetypes=DOC_FILETYPES)
        if path:
            self.tts_path.set(path)
            self._tts_source = Path(path)
            if not self.tts_output.get().strip():
                self.tts_output.set(str(Path(path).with_suffix(".mp3")))

    def _pick_tts_output(self) -> None:
        path = filedialog.asksaveasfilename(
            title="保存语音文件",
            defaultextension=".mp3",
            filetypes=[("MP3 音频", "*.mp3"), ("所有文件", "*.*")],
        )
        if path:
            self.tts_output.set(path)

    def _extract_tts_text(self) -> None:
        text = self.tts_path.get().strip()
        if not text:
            messagebox.showwarning("提示", "请先选择文档。")
            return
        path = Path(text)
        if not path.is_file():
            messagebox.showwarning("提示", f"文件不存在：{path}")
            return

        self._set_busy(True)
        self._start_indeterminate()
        threading.Thread(target=self._run_extract_text, args=(path,), daemon=True).start()

    def _run_extract_text(self, path: Path) -> None:
        self.root.after(0, lambda: self.status.config(text="正在提取文档文字…"))
        try:
            text = extract_text(path)
            self._tts_source = path
            self._tts_text = text
            summary = f"已提取文字：{len(text)} 个字符"
            self.root.after(0, lambda: self._set_preview_text(self.tts_preview, text))
            self.root.after(0, lambda: self._finish(summary))
        except Exception as exc:  # noqa: BLE001
            self.root.after(0, lambda: self._finish_error(f"提取失败: {exc}"))

    def _start_tts(self) -> None:
        text = self._get_preview_text(self.tts_preview)
        if not text:
            messagebox.showwarning("提示", "请先提取文档文字，或在预览区输入要合成的内容。")
            return

        output_text = self.tts_output.get().strip()
        if not output_text:
            source = self._tts_source or Path(self.tts_path.get().strip() or "speech.mp3")
            output_text = str(source.with_suffix(".mp3"))
            self.tts_output.set(output_text)

        output_path = Path(output_text)
        voice = self.tts_voice.get() or "zh-CN-XiaoxiaoNeural"

        self._set_busy(True)
        self._start_indeterminate()
        threading.Thread(
            target=self._run_tts,
            args=(text, output_path, voice, self.tts_rate.get()),
            daemon=True,
        ).start()

    def _run_tts(self, text: str, output_path: Path, voice: str, rate: str) -> None:
        self.root.after(0, lambda: self.status.config(text="正在合成语音（需联网）…"))
        try:
            result = synthesize_speech(text, output_path, voice=voice, rate=rate)
            summary = f"语音已生成：{result}"
            self.root.after(0, lambda: self._finish(summary, output=result))
        except Exception as exc:  # noqa: BLE001
            self.root.after(0, lambda: self._finish_error(f"合成失败: {exc}"))

    def _play_tts_audio(self) -> None:
        path_text = self.tts_output.get().strip()
        if not path_text:
            messagebox.showwarning("提示", "请先生成语音文件。")
            return
        path = Path(path_text)
        if not path.is_file():
            messagebox.showwarning("提示", f"找不到音频文件：{path}")
            return
        try:
            if sys.platform == "darwin":
                subprocess.Popen(["afplay", str(path)])
            elif sys.platform == "win32":
                subprocess.Popen(["start", "", str(path)], shell=True)
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except OSError as exc:
            messagebox.showerror("错误", f"无法播放：{exc}")


def main() -> None:
    root = tk.Tk()
    try:
        style = ttk.Style()
        if sys.platform == "darwin":
            style.theme_use("aqua")
    except tk.TclError:
        pass
    SpeechToolboxApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
