"""录屏：优先 ffmpeg（含系统音频），回退 mss + OpenCV（仅画面）。"""

from __future__ import annotations

import platform
import re
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import mss
import numpy as np


@dataclass
class RecorderState:
    is_recording: bool = False
    started_at: float | None = None
    temp_path: Path | None = None
    uses_audio: bool = False
    backend: str = ""


class ScreenRecorder:
    def __init__(self) -> None:
        self._state = RecorderState()
        self._ffmpeg_proc: subprocess.Popen[bytes] | None = None
        self._fallback_thread: threading.Thread | None = None
        self._fallback_stop = threading.Event()
        self._lock = threading.Lock()

    @property
    def is_recording(self) -> bool:
        with self._lock:
            return self._state.is_recording

    @property
    def uses_audio(self) -> bool:
        with self._lock:
            return self._state.uses_audio

    @property
    def backend(self) -> str:
        with self._lock:
            return self._state.backend

    def elapsed_seconds(self) -> float:
        with self._lock:
            if not self._state.is_recording or self._state.started_at is None:
                return 0.0
            return time.time() - self._state.started_at

    def start(self, temp_path: Path) -> tuple[bool, str]:
        """开始录制，写入临时文件。返回 (成功, 说明信息)。"""
        with self._lock:
            if self._state.is_recording:
                return False, "正在录制中"

        temp_path = temp_path.with_suffix(".mp4")
        temp_path.parent.mkdir(parents=True, exist_ok=True)

        if shutil.which("ffmpeg"):
            ok, msg = self._start_ffmpeg(temp_path)
            if ok:
                return True, msg

        ok, msg = self._start_fallback(temp_path)
        return ok, msg

    def stop(self) -> Path | None:
        """停止录制并返回临时文件路径。"""
        with self._lock:
            if not self._state.is_recording:
                return None
            path = self._state.temp_path

        if self._ffmpeg_proc is not None:
            self._stop_ffmpeg()
        else:
            self._stop_fallback()

        with self._lock:
            self._state.is_recording = False
            self._state.started_at = None
        return path

    # ------------------------------------------------------------------ ffmpeg
    def _start_ffmpeg(self, temp_path: Path) -> tuple[bool, str]:
        system = platform.system()
        if system == "Darwin":
            cmd, uses_audio, note = self._ffmpeg_cmd_macos(temp_path)
        elif system == "Windows":
            cmd, uses_audio, note = self._ffmpeg_cmd_windows(temp_path)
        else:
            cmd, uses_audio, note = self._ffmpeg_cmd_linux(temp_path)

        try:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError as exc:
            return False, f"启动 ffmpeg 失败：{exc}"

        with self._lock:
            self._ffmpeg_proc = proc
            self._state.is_recording = True
            self._state.started_at = time.time()
            self._state.temp_path = temp_path
            self._state.uses_audio = uses_audio
            self._state.backend = "ffmpeg"
        return True, note

    def _stop_ffmpeg(self) -> None:
        proc = self._ffmpeg_proc
        self._ffmpeg_proc = None
        if proc is None:
            return
        try:
            if proc.stdin:
                proc.stdin.write(b"q")
                proc.stdin.flush()
            proc.wait(timeout=8)
        except Exception:
            proc.kill()
            proc.wait(timeout=3)

    def _ffmpeg_cmd_macos(self, path: Path) -> tuple[list[str], bool, str]:
        screen_idx = self._macos_screen_index()
        audio_idx = self._macos_audio_index()
        uses_audio = audio_idx is not None
        input_spec = f"{screen_idx}:{audio_idx}" if uses_audio else f"{screen_idx}:none"
        cmd = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "avfoundation",
            "-framerate",
            "30",
            "-capture_cursor",
            "1",
            "-i",
            input_spec,
            "-pix_fmt",
            "yuv420p",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "23",
        ]
        if uses_audio:
            cmd += ["-c:a", "aac", "-b:a", "192k"]
        cmd.append(str(path))

        if uses_audio and self._is_blackhole_audio(audio_idx):
            note = "录制中（画面 + 系统音频 via BlackHole）"
        elif uses_audio:
            note = "录制中（画面 + 音频）"
        else:
            note = (
                "录制中（仅画面）。要录制系统声音，请安装 BlackHole 并设为系统输出，"
                "详见 README。"
            )
        return cmd, uses_audio, note

    def _ffmpeg_cmd_windows(self, path: Path) -> tuple[list[str], bool, str]:
        audio_name = self._windows_loopback_device()
        uses_audio = audio_name is not None
        cmd = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "gdigrab",
            "-framerate",
            "30",
            "-draw_mouse",
            "1",
            "-i",
            "desktop",
        ]
        if uses_audio:
            cmd += [
                "-f",
                "dshow",
                "-i",
                f"audio={audio_name}",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
            ]
        cmd += [
            "-pix_fmt",
            "yuv420p",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "23",
            str(path),
        ]
        note = "录制中（画面 + 系统音频）" if uses_audio else "录制中（仅画面，未找到环回音频设备）"
        return cmd, uses_audio, note

    def _ffmpeg_cmd_linux(self, path: Path) -> tuple[list[str], bool, str]:
        display = ":0.0"
        audio = "default"
        cmd = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "x11grab",
            "-framerate",
            "30",
            "-i",
            display,
            "-f",
            "pulse",
            "-i",
            audio,
            "-pix_fmt",
            "yuv420p",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "23",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            str(path),
        ]
        return cmd, True, "录制中（画面 + 音频）"

    def _macos_screen_index(self) -> str:
        try:
            result = subprocess.run(
                ["ffmpeg", "-f", "avfoundation", "-list_devices", "true", "-i", ""],
                capture_output=True,
                text=True,
                timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired):
            return "1"

        for line in result.stderr.splitlines():
            match = re.search(r"\[(\d+)\]\s+Capture screen", line)
            if match:
                return match.group(1)
        return "1"

    def _macos_audio_index(self) -> str | None:
        try:
            result = subprocess.run(
                ["ffmpeg", "-f", "avfoundation", "-list_devices", "true", "-i", ""],
                capture_output=True,
                text=True,
                timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None

        text = result.stderr
        in_audio = False
        devices: list[tuple[str, str]] = []
        for line in text.splitlines():
            if "AVFoundation audio devices" in line:
                in_audio = True
                continue
            if "AVFoundation video devices" in line:
                in_audio = False
                continue
            if not in_audio:
                continue
            match = re.search(r"\[(\d+)\]\s+(.+)", line)
            if match:
                devices.append((match.group(1), match.group(2).strip()))

        for idx, name in devices:
            lower = name.lower()
            if "blackhole" in lower:
                return idx

        for idx, name in devices:
            lower = name.lower()
            if any(k in lower for k in ("aggregate", "multi-output", "soundflower")):
                return idx

        for idx, name in devices:
            lower = name.lower()
            if "microphone" in lower or "mic" in lower or "麦克风" in name:
                continue
            if "built-in" in lower or "output" in lower or "扬声器" in name:
                return idx

        return devices[0][0] if devices else None

    def _is_blackhole_audio(self, audio_idx: str | None) -> bool:
        if audio_idx is None:
            return False
        try:
            result = subprocess.run(
                ["ffmpeg", "-f", "avfoundation", "-list_devices", "true", "-i", ""],
                capture_output=True,
                text=True,
                timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired):
            return False
        return f"[{audio_idx}]" in result.stderr and "BlackHole" in result.stderr

    def _windows_loopback_device(self) -> str | None:
        try:
            result = subprocess.run(
                ["ffmpeg", "-list_devices", "true", "-f", "dshow", "-i", "dummy"],
                capture_output=True,
                text=True,
                timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None

        for line in result.stderr.splitlines():
            if "(audio)" not in line:
                continue
            match = re.search(r'"(.+?)"\s+\(audio\)', line)
            if not match:
                continue
            name = match.group(1)
            lower = name.lower()
            if "stereo mix" in lower or "立体声混音" in name:
                return name
        return None

    # ---------------------------------------------------------------- fallback
    def _start_fallback(self, temp_path: Path) -> tuple[bool, str]:
        self._fallback_stop.clear()
        thread = threading.Thread(
            target=self._fallback_loop,
            args=(temp_path,),
            daemon=True,
        )
        with self._lock:
            self._fallback_thread = thread
            self._state.is_recording = True
            self._state.started_at = time.time()
            self._state.temp_path = temp_path
            self._state.uses_audio = False
            self._state.backend = "mss"
        thread.start()
        return True, "录制中（仅画面，未安装 ffmpeg）"

    def _stop_fallback(self) -> None:
        self._fallback_stop.set()
        thread = self._fallback_thread
        if thread and thread.is_alive():
            thread.join(timeout=5)
        self._fallback_thread = None

    def _fallback_loop(self, temp_path: Path) -> None:
        fps = 20.0
        with mss.mss() as sct:
            mon = sct.monitors[0]
            width, height = mon["width"], mon["height"]
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(str(temp_path), fourcc, fps, (width, height))
            if not writer.isOpened():
                with self._lock:
                    self._state.is_recording = False
                return

            interval = 1.0 / fps
            try:
                while not self._fallback_stop.is_set():
                    start = time.time()
                    frame = sct.grab(mon)
                    img = np.array(frame)
                    bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                    writer.write(bgr)
                    elapsed = time.time() - start
                    sleep_for = interval - elapsed
                    if sleep_for > 0:
                        time.sleep(sleep_for)
            finally:
                writer.release()
