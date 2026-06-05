"""OCR engine backends: PaddleOCR (high accuracy) and Tesseract."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal

from PIL import Image, ImageEnhance, ImageOps

from image_utils import check_tesseract, configure_tesseract, get_tesseract_install_hint

OcrProgressCallback = Callable[[int, str], None]

# Reduce Paddle/PaddleX console noise (models still load on first OCR run).
os.environ.setdefault("GLOG_minloglevel", "2")
os.environ.setdefault("FLAGS_minloglevel", "2")

PADDLE_LANG_MAP: dict[str, str] = {
    "chi_sim+eng": "ch",
    "chi_sim": "ch",
    "eng": "en",
    "chi_tra+eng": "chinese_cht",
    "jpn+eng": "japan",
}

_paddle_instances: dict[str, object] = {}


def _quiet_paddle_loggers() -> None:
    for name in ("ppocr", "paddlex", "paddle", "paddleocr"):
        logging.getLogger(name).setLevel(logging.ERROR)


@dataclass
class OcrOptions:
    engine: Literal["paddle", "tesseract"] = "paddle"
    lang: str = "chi_sim+eng"
    preprocess: Literal["auto", "none", "grayscale", "binarize", "strong"] = "auto"
    upscale: bool = True
    min_side: int = 1600
    psm: int = 6
    oem: int = 3
    use_textline_orientation: bool = True
    use_doc_preprocess: bool = False
    min_score: float = 0.5


def paddle_lang_for(lang: str) -> str:
    return PADDLE_LANG_MAP.get(lang, "ch")


def check_paddle_ocr(*, detailed: bool = False) -> tuple[bool, str]:
    """Check PaddleOCR packages without loading OCR models."""
    if importlib.util.find_spec("paddle") is None:
        return False, "未安装 paddlepaddle\n\n请运行：\npip install paddlepaddle"
    if importlib.util.find_spec("paddleocr") is None:
        return False, "未安装 paddleocr\n\n请运行：\npip install paddleocr"

    if not detailed:
        return True, "PaddleOCR 已安装\n点击「开始识别」时加载模型（首次约 1 分钟）"

    try:
        import paddle

        version = paddle.__version__
    except Exception as exc:  # noqa: BLE001
        return False, f"Paddle 无法加载：{exc}"
    return True, f"PaddleOCR 已安装\nPaddle {version}\n模型在首次识别时加载"


def check_ocr_environment(options: OcrOptions) -> tuple[bool, str]:
    if options.engine == "paddle":
        return check_paddle_ocr()
    return check_tesseract(options.lang)


def _upscale_if_needed(img: Image.Image, options: OcrOptions) -> Image.Image:
    if not options.upscale:
        return img
    w, h = img.size
    min_side = min(w, h)
    if min_side < options.min_side:
        scale = options.min_side / min_side
        img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
    return img


def preprocess_for_tesseract(img: Image.Image, options: OcrOptions) -> Image.Image:
    img = _upscale_if_needed(img, options)
    if options.preprocess == "none":
        return img.convert("RGB")

    try:
        import cv2
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("Tesseract 预处理需要 opencv-python-headless") from exc

    gray = np.array(img.convert("L"))
    if options.preprocess in ("auto", "grayscale", "strong"):
        gray = cv2.medianBlur(gray, 3)
    if options.preprocess in ("auto", "strong"):
        gray = cv2.convertScaleAbs(gray, alpha=1.25, beta=15)
    if options.preprocess in ("auto", "binarize", "strong"):
        if options.preprocess == "strong":
            gray = cv2.fastNlMeansDenoising(gray, h=10)
        gray = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 35, 12
        )
    elif options.preprocess == "grayscale":
        gray = np.array(ImageOps.autocontrast(Image.fromarray(gray)))
    return Image.fromarray(gray).convert("RGB")


def preprocess_for_paddle(img: Image.Image, options: OcrOptions) -> Image.Image:
    """PaddleOCR works best on RGB; avoid aggressive binarization."""
    img = _upscale_if_needed(img, options)
    img = img.convert("RGB")
    if options.preprocess == "none":
        return img
    img = ImageOps.autocontrast(img)
    if options.preprocess in ("strong", "binarize"):
        img = ImageEnhance.Contrast(img).enhance(1.25)
        img = ImageEnhance.Sharpness(img).enhance(1.4)
    return img


def _get_paddle_ocr(options: OcrOptions, on_progress: OcrProgressCallback | None = None):
    lang = paddle_lang_for(options.lang)
    key = f"{lang}|{options.use_textline_orientation}|{options.use_doc_preprocess}"
    if key not in _paddle_instances:
        if on_progress:
            on_progress(20, "正在加载 PaddleOCR 模型（仅首次，约 1 分钟）…")
        _quiet_paddle_loggers()
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
            from paddleocr import PaddleOCR

            _paddle_instances[key] = PaddleOCR(
                lang=lang,
                use_textline_orientation=options.use_textline_orientation,
                use_doc_orientation_classify=options.use_doc_preprocess,
                use_doc_unwarping=options.use_doc_preprocess,
            )
        if on_progress:
            on_progress(45, "模型加载完成")
    return _paddle_instances[key]


def _paddle_pages_to_text(pages: list, min_score: float) -> str:
    lines: list[str] = []
    for page in pages:
        if not isinstance(page, dict):
            continue
        texts = page.get("rec_texts") or []
        scores = page.get("rec_scores") or [1.0] * len(texts)
        for text, score in zip(texts, scores):
            cleaned = str(text).strip()
            if cleaned and float(score) >= min_score:
                lines.append(cleaned)
    return "\n".join(lines)


def run_paddle_ocr(
    img: Image.Image,
    options: OcrOptions,
    on_progress: OcrProgressCallback | None = None,
) -> str:
    import numpy as np

    def report(pct: int, msg: str) -> None:
        if on_progress:
            on_progress(pct, msg)

    report(10, "检查 PaddleOCR 环境…")
    ready, message = check_paddle_ocr()
    if not ready:
        raise RuntimeError(message)

    ocr = _get_paddle_ocr(options, on_progress=on_progress)
    report(55, "正在识别文字（可能需要数十秒，请稍候）…")
    pages = ocr.predict(np.array(img))
    report(85, "正在整理识别结果…")
    text = _paddle_pages_to_text(pages, options.min_score)
    report(100, "识别完成")
    return text.strip()


def run_tesseract_ocr(
    img: Image.Image,
    options: OcrOptions,
    on_progress: OcrProgressCallback | None = None,
) -> str:
    import pytesseract

    def report(pct: int, msg: str) -> None:
        if on_progress:
            on_progress(pct, msg)

    report(10, "检查 Tesseract 环境…")
    ready, message = check_tesseract(options.lang)
    if not ready:
        raise RuntimeError(message)

    configure_tesseract()
    config = f"--oem {options.oem} --psm {options.psm}"
    report(40, "正在识别文字…")
    try:
        text = pytesseract.image_to_string(img, lang=options.lang, config=config)
    except pytesseract.TesseractNotFoundError as exc:
        raise RuntimeError(f"未找到 Tesseract OCR 引擎。\n\n{get_tesseract_install_hint()}") from exc
    except pytesseract.TesseractError as exc:
        err = str(exc)
        if "Error opening data file" in err or "Failed loading language" in err:
            raise RuntimeError(f"OCR 语言包不可用（{options.lang}）。\n\n{get_tesseract_install_hint()}") from exc
        raise RuntimeError(f"OCR 识别失败：{err}") from exc
    report(100, "识别完成")
    return text.strip()


def run_ocr(
    source: Path,
    options: OcrOptions | None = None,
    on_progress: OcrProgressCallback | None = None,
) -> str:
    opts = options or OcrOptions()

    def report(pct: int, msg: str) -> None:
        if on_progress:
            on_progress(pct, msg)

    report(2, "正在读取图片…")
    img = Image.open(source)

    report(8, "正在预处理图片…")
    if opts.engine == "paddle":
        img = preprocess_for_paddle(img, opts)
        return run_paddle_ocr(img, opts, on_progress=on_progress)

    img = preprocess_for_tesseract(img, opts)
    return run_tesseract_ocr(img, opts, on_progress=on_progress)
