#!/usr/bin/env python3
"""将 PDF 文件转换为 Word (.docx) 文档。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pdf2docx import Converter


def convert_pdf(pdf_path: Path, docx_path: Path | None = None) -> Path:
    """转换单个 PDF 为 DOCX，返回输出文件路径。"""
    if not pdf_path.is_file():
        raise FileNotFoundError(f"找不到 PDF 文件: {pdf_path}")
    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError(f"不是 PDF 文件: {pdf_path}")

    output = docx_path or pdf_path.with_suffix(".docx")
    output.parent.mkdir(parents=True, exist_ok=True)

    cv = Converter(str(pdf_path))
    try:
        cv.convert(str(output))
    finally:
        cv.close()

    return output


def collect_pdfs(inputs: list[Path], recursive: bool) -> list[Path]:
    """从输入路径收集所有 PDF 文件。"""
    pdfs: list[Path] = []
    for item in inputs:
        if item.is_file():
            if item.suffix.lower() == ".pdf":
                pdfs.append(item)
            else:
                print(f"跳过（非 PDF）: {item}", file=sys.stderr)
        elif item.is_dir():
            pattern = "**/*.pdf" if recursive else "*.pdf"
            pdfs.extend(sorted(item.glob(pattern)))
        else:
            print(f"跳过（路径不存在）: {item}", file=sys.stderr)
    return pdfs


def resolve_docx_path(
    pdf: Path,
    output: Path | None,
    *,
    batch_mode: bool,
) -> Path:
    """根据输出设置计算单个 PDF 对应的 DOCX 路径。"""
    if output is None:
        return pdf.with_suffix(".docx")
    if output.is_dir() or (batch_mode and not output.suffix):
        out_dir = output if output.is_dir() else output
        out_dir.mkdir(parents=True, exist_ok=True)
        return out_dir / pdf.with_suffix(".docx").name
    return output


def main() -> int:
    parser = argparse.ArgumentParser(
        description="将 PDF 转换为 Word (.docx) 文档",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s report.pdf
  %(prog)s report.pdf -o report.docx
  %(prog)s ./pdfs/ -o ./output/
  %(prog)s ./pdfs/ -r
        """,
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        type=Path,
        help="PDF 文件或包含 PDF 的目录",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="输出 .docx 路径，或批量转换时的输出目录",
    )
    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help="递归扫描子目录中的 PDF",
    )
    args = parser.parse_args()

    pdfs = collect_pdfs(args.inputs, args.recursive)
    if not pdfs:
        print("未找到任何 PDF 文件。", file=sys.stderr)
        return 1

    output = args.output
    batch_mode = len(pdfs) > 1 or any(p.is_dir() for p in args.inputs)
    if batch_mode and output and output.suffix.lower() == ".docx":
        print("批量转换时 --output 请指定目录而非 .docx 文件。", file=sys.stderr)
        return 1

    failed = 0
    for pdf in pdfs:
        try:
            docx = resolve_docx_path(pdf, output, batch_mode=batch_mode)
            result = convert_pdf(pdf, docx)
            print(f"完成: {pdf} -> {result}")
        except Exception as exc:  # noqa: BLE001 — CLI 需汇总所有失败
            print(f"失败: {pdf} ({exc})", file=sys.stderr)
            failed += 1

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
