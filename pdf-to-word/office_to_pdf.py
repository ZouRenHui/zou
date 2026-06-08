#!/usr/bin/env python3
"""Word / PPT 等办公文档转 PDF。"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

OFFICE_SUFFIXES = {".doc", ".docx", ".ppt", ".pptx", ".odt", ".odp", ".rtf"}
TEXTUTIL_SUFFIXES = {".doc", ".docx", ".rtf", ".txt", ".html"}


def collect_office_files(inputs: list[Path], recursive: bool) -> list[Path]:
    """从输入路径收集办公文档。"""
    files: list[Path] = []
    for item in inputs:
        if item.is_file():
            if item.suffix.lower() in OFFICE_SUFFIXES:
                files.append(item)
        elif item.is_dir():
            pattern = "**/*" if recursive else "*"
            for path in sorted(item.glob(pattern)):
                if path.is_file() and path.suffix.lower() in OFFICE_SUFFIXES:
                    files.append(path)
    return files


def resolve_pdf_output(source: Path, output: Path | None, *, batch_mode: bool) -> Path:
    """计算输出 PDF 路径。"""
    if output is None:
        return source.with_suffix(".pdf")
    if output.is_dir() or (batch_mode and not output.suffix):
        out_dir = output if output.is_dir() else output
        out_dir.mkdir(parents=True, exist_ok=True)
        return out_dir / source.with_suffix(".pdf").name
    return output


def convert_office_to_pdf(source: Path, output_path: Path | None = None) -> Path:
    """将 Word/PPT 等文件转为 PDF。"""
    if not source.is_file():
        raise FileNotFoundError(f"找不到文件: {source}")
    suffix = source.suffix.lower()
    if suffix not in OFFICE_SUFFIXES:
        raise ValueError(f"不支持的文件类型: {suffix}")

    output = output_path or source.with_suffix(".pdf")
    if output.suffix.lower() != ".pdf":
        output = output.with_suffix(".pdf")
    output.parent.mkdir(parents=True, exist_ok=True)

    errors: list[str] = []

    for converter in (
        _convert_with_libreoffice,
        _convert_with_docx2pdf,
        _convert_with_textutil,
        _convert_with_ms_office,
    ):
        try:
            return converter(source, output)
        except Exception as exc:  # noqa: BLE001
            errors.append(str(exc))

    hint = _install_hint()
    detail = "\n".join(f"- {e}" for e in errors)
    raise RuntimeError(f"无法转换为 PDF。\n{detail}\n\n{hint}")


def _install_hint() -> str:
    if sys.platform == "darwin":
        return (
            "请安装 LibreOffice（推荐，支持 Word/PPT）：\n"
            "  brew install --cask libreoffice\n"
            "Mac 上也可仅用系统 textutil 转换 Word（.doc/.docx），但 PPT 需 LibreOffice。"
        )
    if sys.platform == "win32":
        return (
            "请安装 LibreOffice 或 Microsoft Office：\n"
            "  https://www.libreoffice.org/download/download/"
        )
    return (
        "请安装 LibreOffice：\n"
        "  sudo apt install libreoffice   # 麒麟 / Debian\n"
        "  sudo dnf install libreoffice   # Fedora"
    )


def find_soffice() -> Path | None:
    """查找 LibreOffice soffice 可执行文件。"""
    candidates: list[str] = []
    if sys.platform == "darwin":
        candidates.append("/Applications/LibreOffice.app/Contents/MacOS/soffice")
    elif sys.platform == "win32":
        for env in ("ProgramFiles", "ProgramFiles(x86)"):
            base = os.environ.get(env)
            if base:
                candidates.append(str(Path(base) / "LibreOffice" / "program" / "soffice.exe"))
    candidates.extend(["soffice", "libreoffice"])

    for item in candidates:
        found = shutil.which(item) if "/" not in item and "\\" not in item else item
        if found and Path(found).is_file():
            return Path(found)
    return None


def _convert_with_libreoffice(source: Path, output: Path) -> Path:
    soffice = find_soffice()
    if not soffice:
        raise RuntimeError("未找到 LibreOffice (soffice)")

    out_dir = output.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(soffice),
        "--headless",
        "--norestore",
        "--convert-to",
        "pdf",
        "--outdir",
        str(out_dir),
        str(source.resolve()),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(f"LibreOffice 转换失败: {err or proc.returncode}")

    produced = out_dir / f"{source.stem}.pdf"
    if not produced.is_file():
        raise RuntimeError("LibreOffice 未生成 PDF 文件")

    if produced.resolve() != output.resolve():
        if output.exists():
            output.unlink()
        produced.replace(output)

    return output


def _convert_with_docx2pdf(source: Path, output: Path) -> Path:
    if sys.platform not in ("darwin", "win32"):
        raise RuntimeError("docx2pdf 仅适用于 macOS / Windows")
    if source.suffix.lower() not in {".doc", ".docx"}:
        raise RuntimeError("docx2pdf 仅支持 Word 文档")

    try:
        from docx2pdf import convert
    except ImportError as exc:
        raise RuntimeError("未安装 docx2pdf（pip install docx2pdf）") from exc

    convert(str(source.resolve()), str(output.resolve()))
    if not output.is_file():
        raise RuntimeError("docx2pdf 未生成 PDF 文件")
    return output


def _convert_with_textutil(source: Path, output: Path) -> Path:
    if sys.platform != "darwin":
        raise RuntimeError("textutil 仅适用于 macOS")
    if source.suffix.lower() not in TEXTUTIL_SUFFIXES:
        raise RuntimeError(f"textutil 不支持 {source.suffix}，PPT 请使用 LibreOffice")

    cmd = ["textutil", "-convert", "pdf", "-output", str(output), str(source.resolve())]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(f"textutil 转换失败: {err or proc.returncode}")
    if not output.is_file():
        raise RuntimeError("textutil 未生成 PDF 文件")
    return output


def _convert_with_ms_office(source: Path, output: Path) -> Path:
    if sys.platform != "win32":
        raise RuntimeError("Microsoft Office COM 仅适用于 Windows")

    try:
        import comtypes.client  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError("未安装 comtypes，无法调用 Microsoft Office") from exc

    suffix = source.suffix.lower()
    src = str(source.resolve())
    dst = str(output.resolve())

    if suffix in {".doc", ".docx", ".rtf"}:
        app = comtypes.client.CreateObject("Word.Application")
        app.Visible = False
        try:
            doc = app.Documents.Open(src, ReadOnly=True)
            try:
                doc.ExportAsFixedFormat(dst, 17)  # wdExportFormatPDF
            finally:
                doc.Close(False)
        finally:
            app.Quit()
    elif suffix in {".ppt", ".pptx"}:
        app = comtypes.client.CreateObject("PowerPoint.Application")
        try:
            presentation = app.Presentations.Open(src, WithWindow=False)
            try:
                presentation.SaveAs(dst, 32)  # ppSaveAsPDF
            finally:
                presentation.Close()
        finally:
            app.Quit()
    else:
        raise RuntimeError(f"Microsoft Office 不支持直接转换: {suffix}")

    if not output.is_file():
        raise RuntimeError("Microsoft Office 未生成 PDF 文件")
    return output
