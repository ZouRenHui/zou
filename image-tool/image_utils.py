"""Shared helpers for image file discovery and output paths."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp", ".tiff", ".tif"}

OUTPUT_FORMATS: dict[str, str] = {
    "JPEG (.jpg)": ".jpg",
    "PNG (.png)": ".png",
    "WebP (.webp)": ".webp",
    "BMP (.bmp)": ".bmp",
    "GIF (.gif)": ".gif",
    "TIFF (.tiff)": ".tiff",
}

QUALITY_PRESETS: dict[str, int] = {
    "原画 (100)": 100,
    "高质量 (92)": 92,
    "标准 (85)": 85,
    "网页 (75)": 75,
    "高压缩 (60)": 60,
    "极小 (40)": 40,
}

LOSSY_EXTENSIONS = {".jpg", ".jpeg", ".webp"}

TESSERACT_CANDIDATES = [
    "/opt/homebrew/bin/tesseract",
    "/usr/local/bin/tesseract",
    "/opt/local/bin/tesseract",
    "/usr/bin/tesseract",
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
]


def is_image(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS


def collect_images(paths: list[Path], recursive: bool = False) -> list[Path]:
    """Collect image files from paths (files or directories)."""
    found: list[Path] = []
    seen: set[Path] = set()

    for raw in paths:
        path = raw.resolve()
        if path.is_file():
            if is_image(path) and path not in seen:
                seen.add(path)
                found.append(path)
            continue
        if not path.is_dir():
            continue
        iterator = path.rglob("*") if recursive else path.glob("*")
        for item in sorted(iterator, key=lambda p: str(p).lower()):
            if is_image(item):
                key = item.resolve()
                if key not in seen:
                    seen.add(key)
                    found.append(item)

    return found


def resolve_output_path(
    source: Path,
    output_dir: Path | None,
    *,
    batch_mode: bool,
    suffix: str = "",
    new_ext: str | None = None,
) -> Path:
    """Resolve destination path for a processed image."""
    ext = new_ext if new_ext else source.suffix
    stem = source.stem + suffix if suffix else source.stem
    name = f"{stem}{ext}"

    if output_dir is None:
        return source.parent / name

    output_dir.mkdir(parents=True, exist_ok=True)
    if batch_mode:
        return output_dir / name
    return output_dir / name


def find_tesseract() -> Path | None:
    """Locate the Tesseract OCR executable."""
    found = shutil.which("tesseract")
    if found:
        return Path(found)
    for candidate in TESSERACT_CANDIDATES:
        path = Path(candidate)
        if path.is_file():
            return path
    return None


def get_tesseract_install_hint() -> str:
    if sys.platform == "darwin":
        return "macOS 请在终端运行：\nbrew install tesseract tesseract-lang"
    if sys.platform == "win32":
        return "Windows 请从以下地址下载安装，并加入 PATH：\nhttps://github.com/UB-Mannheim/tesseract/wiki"
    return "Linux 请运行：\nsudo apt install tesseract-ocr tesseract-ocr-chi-sim   # Debian/Ubuntu"


def check_tesseract(lang: str = "chi_sim") -> tuple[bool, str]:
    """Return (ready, status_message) for OCR."""
    binary = find_tesseract()
    if not binary:
        return False, f"未找到 Tesseract OCR 引擎\n\n{get_tesseract_install_hint()}"

    try:
        result = subprocess.run(
            [str(binary), "--list-langs"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except OSError as exc:
        return False, f"Tesseract 无法运行：{exc}"

    if result.returncode != 0:
        return False, f"Tesseract 运行异常：{result.stderr.strip() or result.stdout.strip()}"

    langs = {line.strip() for line in result.stdout.splitlines() if line.strip()}
    langs.discard("")

    missing = [part for part in lang.split("+") if part and part not in langs]
    if missing:
        hint = get_tesseract_install_hint()
        return False, f"缺少语言包：{', '.join(missing)}\n\n{hint}"

    version = ""
    try:
        ver = subprocess.run(
            [str(binary), "--version"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        if ver.stdout:
            version = ver.stdout.splitlines()[0]
    except OSError:
        pass

    loc = f" ({binary})" if binary.name != "tesseract" else ""
    msg = f"OCR 就绪{loc}"
    if version:
        msg += f"\n{version}"
    return True, msg


def configure_tesseract() -> Path:
    """Configure pytesseract to use the detected Tesseract binary."""
    import pytesseract

    binary = find_tesseract()
    if not binary:
        raise RuntimeError(f"未找到 Tesseract OCR 引擎。\n\n{get_tesseract_install_hint()}")
    pytesseract.pytesseract.tesseract_cmd = str(binary)
    return binary


def format_file_size(size_bytes: int) -> str:
    """Human-readable file size."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.2f} MB"


def find_system_font() -> str | None:
    """Return a usable TrueType font path for watermark text."""
    candidates = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    ]
    for path in candidates:
        if Path(path).is_file():
            return path
    return None
