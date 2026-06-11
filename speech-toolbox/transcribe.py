#!/usr/bin/env python3
"""音频 / 视频语音识别。"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

AUDIO_SUFFIXES = {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".wma"}
VIDEO_SUFFIXES = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".wmv", ".flv", ".m4v"}
MEDIA_SUFFIXES = AUDIO_SUFFIXES | VIDEO_SUFFIXES

WHISPER_MODELS = ("tiny", "base", "small", "medium", "large-v3")


@dataclass
class TranscriptSegment:
    start: float
    end: float
    text: str


@dataclass
class TranscriptResult:
    text: str
    segments: list[TranscriptSegment]
    language: str | None


def is_media_file(path: Path) -> bool:
    return path.suffix.lower() in MEDIA_SUFFIXES


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def prepare_audio(media_path: Path) -> tuple[Path, tempfile.TemporaryDirectory | None]:
    """将媒体文件转为 16kHz 单声道 WAV；纯音频文件可直接返回。"""
    suffix = media_path.suffix.lower()
    if suffix == ".wav":
        return media_path, None

    if not ffmpeg_available():
        if suffix in AUDIO_SUFFIXES:
            return media_path, None
        raise RuntimeError("处理视频需要安装 ffmpeg（https://ffmpeg.org/）")

    temp_dir = tempfile.TemporaryDirectory(prefix="speech-toolbox-")
    wav_path = Path(temp_dir.name) / "audio.wav"
    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(media_path),
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",
        "-ac",
        "1",
        str(wav_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        temp_dir.cleanup()
        stderr = (result.stderr or "").strip() or "ffmpeg 提取音频失败"
        raise RuntimeError(stderr)
    return wav_path, temp_dir


def transcribe_media(
    media_path: Path,
    *,
    model: str = "base",
    language: str | None = None,
    progress_callback=None,
) -> TranscriptResult:
    """识别音频或视频中的语音。"""
    if not media_path.is_file():
        raise FileNotFoundError(f"找不到文件: {media_path}")
    if media_path.suffix.lower() not in MEDIA_SUFFIXES:
        raise ValueError(f"不支持的媒体格式: {media_path.suffix}")

    if model not in WHISPER_MODELS:
        raise ValueError(f"不支持的模型: {model}")

    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError("未安装 faster-whisper，请运行: pip install faster-whisper") from exc

    audio_path, temp_dir = prepare_audio(media_path)
    try:
        if progress_callback:
            progress_callback("正在加载语音识别模型…")

        whisper = WhisperModel(model, device="cpu", compute_type="int8")
        if progress_callback:
            progress_callback("正在识别语音…")

        segments_iter, info = whisper.transcribe(
            str(audio_path),
            language=language or None,
            vad_filter=True,
        )

        segments: list[TranscriptSegment] = []
        lines: list[str] = []
        for segment in segments_iter:
            text = segment.text.strip()
            if not text:
                continue
            segments.append(TranscriptSegment(segment.start, segment.end, text))
            lines.append(text)
            if progress_callback:
                progress_callback(f"识别中… {segment.end:.0f}s")

        return TranscriptResult(
            text="\n".join(lines),
            segments=segments,
            language=getattr(info, "language", None),
        )
    finally:
        if temp_dir is not None:
            temp_dir.cleanup()
