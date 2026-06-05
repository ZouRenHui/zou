#!/usr/bin/env python3
"""PDF 拼接与拆分工具函数。"""

from __future__ import annotations

import re
from pathlib import Path

import fitz


def merge_pdfs(inputs: list[Path], output_path: Path) -> Path:
    """将多个 PDF 按顺序拼接为一个文件。"""
    if len(inputs) < 2:
        raise ValueError("拼接至少需要 2 个 PDF 文件")
    if output_path.suffix.lower() != ".pdf":
        raise ValueError("输出文件必须是 .pdf")

    for path in inputs:
        if not path.is_file():
            raise FileNotFoundError(f"找不到文件: {path}")
        if path.suffix.lower() != ".pdf":
            raise ValueError(f"不是 PDF 文件: {path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    merged = fitz.open()
    try:
        for path in inputs:
            doc = fitz.open(str(path))
            try:
                merged.insert_pdf(doc)
            finally:
                doc.close()
        merged.save(str(output_path))
    finally:
        merged.close()

    return output_path


def parse_page_ranges(spec: str, page_count: int) -> list[tuple[int, int]]:
    """
    解析页码范围字符串，返回 0-based 的 (start, end) 列表（均含端点）。

    示例: "1-3, 5, 7-10" -> [(0, 2), (4, 4), (6, 9)]
    """
    text = spec.strip()
    if not text:
        raise ValueError("请输入页码范围")

    ranges: list[tuple[int, int]] = []
    for part in re.split(r"[，,;；\s]+", text):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start_s, end_s = part.split("-", 1)
            start = int(start_s.strip())
            end = int(end_s.strip())
        else:
            start = end = int(part)

        if start < 1 or end < 1:
            raise ValueError(f"页码必须 >= 1: {part}")
        if start > end:
            raise ValueError(f"起始页不能大于结束页: {part}")
        if end > page_count:
            raise ValueError(f"页码 {end} 超出总页数 {page_count}")

        ranges.append((start - 1, end - 1))

    if not ranges:
        raise ValueError("未解析到有效页码范围")

    return ranges


def split_pdf_each_page(input_path: Path, output_dir: Path) -> list[Path]:
    """将 PDF 按页拆分为多个单页文件。"""
    _validate_pdf(input_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(str(input_path))
    results: list[Path] = []
    try:
        stem = input_path.stem
        for i in range(doc.page_count):
            part = fitz.open()
            try:
                part.insert_pdf(doc, from_page=i, to_page=i)
                out = output_dir / f"{stem}_第{i + 1}页.pdf"
                part.save(str(out))
                results.append(out)
            finally:
                part.close()
    finally:
        doc.close()

    return results


def split_pdf_by_ranges(
    input_path: Path,
    output_dir: Path,
    ranges_spec: str,
) -> list[Path]:
    """按页码范围拆分 PDF。"""
    _validate_pdf(input_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(str(input_path))
    results: list[Path] = []
    try:
        page_ranges = parse_page_ranges(ranges_spec, doc.page_count)
        stem = input_path.stem
        for idx, (start, end) in enumerate(page_ranges, start=1):
            part = fitz.open()
            try:
                part.insert_pdf(doc, from_page=start, to_page=end)
                label = f"第{start + 1}-{end + 1}页" if start != end else f"第{start + 1}页"
                out = output_dir / f"{stem}_{label}.pdf"
                part.save(str(out))
                results.append(out)
            finally:
                part.close()
    finally:
        doc.close()

    return results


def _validate_pdf(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"找不到 PDF 文件: {path}")
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"不是 PDF 文件: {path}")
