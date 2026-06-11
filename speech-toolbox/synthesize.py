#!/usr/bin/env python3
"""文字转语音（基于 edge-tts）。"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

DEFAULT_VOICES = [
    ("晓晓（女声，普通话）", "zh-CN-XiaoxiaoNeural"),
    ("云希（男声，普通话）", "zh-CN-YunxiNeural"),
    ("晓伊（女声，普通话）", "zh-CN-XiaoyiNeural"),
    ("云健（男声，普通话）", "zh-CN-YunjianNeural"),
    ("晓萱（女声，台湾）", "zh-TW-HsiaoChenNeural"),
    ("Jenny（女声，英语）", "en-US-JennyNeural"),
    ("Guy（男声，英语）", "en-US-GuyNeural"),
]


@dataclass
class VoiceOption:
    label: str
    voice_id: str


def list_voices() -> list[VoiceOption]:
    return [VoiceOption(label, voice_id) for label, voice_id in DEFAULT_VOICES]


def synthesize_speech(
    text: str,
    output_path: Path,
    *,
    voice: str = "zh-CN-XiaoxiaoNeural",
    rate: str = "+0%",
) -> Path:
    """将文本合成为 MP3 文件。"""
    cleaned = text.strip()
    if not cleaned:
        raise ValueError("没有可合成的文字内容")

    try:
        import edge_tts
    except ImportError as exc:
        raise RuntimeError("未安装 edge-tts，请运行: pip install edge-tts") from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)

    async def _run() -> None:
        communicate = edge_tts.Communicate(cleaned, voice=voice, rate=rate)
        await communicate.save(str(output_path))

    asyncio.run(_run())
    if not output_path.is_file():
        raise RuntimeError("语音合成失败，未生成输出文件")
    return output_path
