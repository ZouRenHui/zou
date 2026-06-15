"""录屏：优先 ffmpeg（含系统音频），回退 mss + OpenCV（仅画面）。"""

from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import mss
import numpy as np

_STARTUP_WAIT_SEC = 1.2


@dataclass
class RecorderState:
    is_recording: bool = False
    started_at: float | None = None
    temp_path: Path | None = None
    uses_audio: bool = False
    backend: str = ""


@dataclass(frozen=True)
class FfmpegAttempt:
    cmd: list[str]
    uses_audio: bool
    note: str


def _subprocess_run_kwargs() -> dict:
    if platform.system() != "Windows":
        return {}
    return {"creationflags": subprocess.CREATE_NO_WINDOW}


def _subprocess_popen_kwargs() -> dict:
    if platform.system() != "Windows":
        return {}
    return {"creationflags": subprocess.CREATE_NO_WINDOW}


def _summarize_ffmpeg_error(text: str) -> str:
    text = text.strip()
    if not text:
        return "ffmpeg 异常退出（无错误输出）"
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    for ln in reversed(lines):
        lower = ln.lower()
        if any(k in lower for k in ("error", "failed", "invalid", "not found", "cannot")):
            return ln[:300]
    return lines[-1][:300]


class ScreenRecorder:
    def __init__(self) -> None:
        self._state = RecorderState()
        self._ffmpeg_proc: subprocess.Popen[bytes] | None = None
        self._fallback_thread: threading.Thread | None = None
        self._fallback_stop = threading.Event()
        self._lock = threading.Lock()
        self._last_error = ""

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

    @property
    def last_error(self) -> str:
        return self._last_error

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

        self._last_error = ""
        temp_path = temp_path.with_suffix(".mp4")
        temp_path.parent.mkdir(parents=True, exist_ok=True)
        if temp_path.exists():
            temp_path.unlink()

        if shutil.which("ffmpeg"):
            for attempt in self._ffmpeg_attempts(temp_path):
                ok, err = self._try_start_ffmpeg(attempt, temp_path)
                if ok:
                    return True, attempt.note
                if err:
                    self._last_error = err

        ok, msg = self._start_fallback(temp_path)
        if self._last_error:
            msg = f"{msg}（ffmpeg：{self._last_error}）"
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
    def _ffmpeg_attempts(self, temp_path: Path) -> list[FfmpegAttempt]:
        system = platform.system()
        if system == "Darwin":
            return [self._attempt_macos(temp_path)]
        if system == "Windows":
            return self._attempts_windows(temp_path)
        return [self._attempt_linux(temp_path)]

    def _try_start_ffmpeg(self, attempt: FfmpegAttempt, temp_path: Path) -> tuple[bool, str]:
        stderr_path = Path(tempfile.gettempdir()) / f"screen_rec_ff_{os.getpid()}_{time.time_ns()}.log"
        stderr_handle = open(stderr_path, "w", encoding="utf-8", errors="replace")
        proc: subprocess.Popen[bytes] | None = None
        try:
            proc = subprocess.Popen(
                attempt.cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=stderr_handle,
                **_subprocess_popen_kwargs(),
            )
        except OSError as exc:
            stderr_handle.close()
            stderr_path.unlink(missing_ok=True)
            return False, f"启动 ffmpeg 失败：{exc}"
        finally:
            try:
                stderr_handle.close()
            except OSError:
                pass

        time.sleep(_STARTUP_WAIT_SEC)
        if proc.poll() is not None:
            err_text = stderr_path.read_text(encoding="utf-8", errors="replace")
            stderr_path.unlink(missing_ok=True)
            if temp_path.exists() and temp_path.stat().st_size == 0:
                temp_path.unlink(missing_ok=True)
            return False, _summarize_ffmpeg_error(err_text)

        stderr_path.unlink(missing_ok=True)
        with self._lock:
            self._ffmpeg_proc = proc
            self._state.is_recording = True
            self._state.started_at = time.time()
            self._state.temp_path = temp_path
            self._state.uses_audio = attempt.uses_audio
            self._state.backend = "ffmpeg"
        return True, ""

    def _stop_ffmpeg(self) -> None:
        proc = self._ffmpeg_proc
        self._ffmpeg_proc = None
        if proc is None:
            return
        try:
            if proc.poll() is None:
                try:
                    if proc.stdin:
                        proc.stdin.write(b"q")
                        proc.stdin.flush()
                        proc.stdin.close()
                except OSError:
                    pass
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.terminate()
                    try:
                        proc.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait(timeout=3)
        except Exception:
            try:
                proc.kill()
            except OSError:
                pass

    def _attempt_macos(self, path: Path) -> FfmpegAttempt:
        screen_idx = self._macos_screen_index()
        audio_idx = self._macos_audio_index()
        uses_audio = audio_idx is not None
        input_spec = f"{screen_idx}:{audio_idx}" if uses_audio else f"{screen_idx}:none"
        cmd = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "warning",
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
            note = "录制中（仅画面，未检测到可用音频设备）"
        return FfmpegAttempt(cmd, uses_audio, note)

    def _attempts_windows(self, path: Path) -> list[FfmpegAttempt]:
        attempts: list[FfmpegAttempt] = []
        for audio_type, audio_name in self._windows_audio_devices():
            if audio_type == "wasapi":
                label = "WASAPI 环回"
            else:
                label = audio_name
            attempts.append(
                FfmpegAttempt(
                    self._ffmpeg_cmd_windows(path, audio_type, audio_name, "libx264"),
                    True,
                    f"录制中（画面 + 系统音频：{label}）",
                )
            )
        attempts.append(
            FfmpegAttempt(
                self._ffmpeg_cmd_windows(path, None, None, "libx264"),
                False,
                "录制中（仅画面）",
            )
        )
        attempts.append(
            FfmpegAttempt(
                self._ffmpeg_cmd_windows(path, None, None, "h264_mf"),
                False,
                "录制中（仅画面，兼容模式）",
            )
        )
        return attempts

    def _ffmpeg_cmd_windows(
        self,
        path: Path,
        audio_type: str | None,
        audio_name: str | None,
        video_encoder: str,
    ) -> list[str]:
        cmd = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "warning",
            "-thread_queue_size",
            "512",
            "-f",
            "gdigrab",
            "-draw_mouse",
            "1",
            "-framerate",
            "30",
            "-i",
            "desktop",
        ]
        if audio_type == "wasapi" and audio_name:
            cmd += [
                "-thread_queue_size",
                "512",
                "-f",
                "wasapi",
                "-loopback",
                "1",
                "-i",
                audio_name,
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
            ]
        elif audio_type == "dshow" and audio_name:
            cmd += [
                "-thread_queue_size",
                "512",
                "-f",
                "dshow",
                "-i",
                f"audio={audio_name}",
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
            ]
        cmd += [
            "-pix_fmt",
            "yuv420p",
            "-c:v",
            video_encoder,
        ]
        if video_encoder == "libx264":
            cmd += ["-preset", "veryfast", "-crf", "23"]
        cmd.append(str(path))
        return cmd

    def _attempt_linux(self, path: Path) -> FfmpegAttempt:
        display = ":0.0"
        audio = "default"
        cmd = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "warning",
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
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
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
        return FfmpegAttempt(cmd, True, "录制中（画面 + 音频）")

    def _run_ffmpeg_list(self, args: list[str]) -> str:
        try:
            result = subprocess.run(
                ["ffmpeg", "-hide_banner", *args],
                capture_output=True,
                text=True,
                timeout=15,
                **_subprocess_run_kwargs(),
            )
        except (OSError, subprocess.TimeoutExpired):
            return ""
        return result.stderr

    def _windows_audio_devices(self) -> list[tuple[str, str]]:
        devices: list[tuple[str, str]] = []
        seen: set[str] = set()

        wasapi_text = self._run_ffmpeg_list(["-list_devices", "true", "-f", "wasapi", "-i", "dummy"])
        for line in wasapi_text.splitlines():
            if "(loopback)" not in line.lower():
                continue
            match = re.search(r'"([^"]+)"', line)
            if match:
                name = match.group(1)
                if name not in seen:
                    seen.add(name)
                    devices.append(("wasapi", name))

        if not devices:
            in_section = False
            for line in wasapi_text.splitlines():
                if "wasapi" in line.lower() and "devices" in line.lower():
                    in_section = True
                    continue
                if in_section and "(audio)" in line.lower():
                    match = re.search(r'"([^"]+)"', line)
                    if not match:
                        continue
                    name = match.group(1)
                    lower = name.lower()
                    if any(k in lower for k in ("microphone", "mic", "麦克风", "input")):
                        continue
                    if name not in seen:
                        seen.add(name)
                        devices.append(("wasapi", name))

        dshow_text = self._run_ffmpeg_list(["-list_devices", "true", "-f", "dshow", "-i", "dummy"])
        for line in dshow_text.splitlines():
            if "(audio)" not in line:
                continue
            match = re.search(r'"([^"]+)"\s+\(audio\)', line)
            if not match:
                continue
            name = match.group(1)
            lower = name.lower()
            if any(k in lower for k in ("stereo mix", "wave out mix", "what u hear", "立体声混音", "混音")):
                if name not in seen:
                    seen.add(name)
                    devices.append(("dshow", name))
        return devices

    def _macos_screen_index(self) -> str:
        text = self._run_ffmpeg_list(["-f", "avfoundation", "-list_devices", "true", "-i", ""])
        for line in text.splitlines():
            match = re.search(r"\[(\d+)\]\s+Capture screen", line)
            if match:
                return match.group(1)
        return "1"

    def _macos_audio_index(self) -> str | None:
        text = self._run_ffmpeg_list(["-f", "avfoundation", "-list_devices", "true", "-i", ""])
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
        text = self._run_ffmpeg_list(["-f", "avfoundation", "-list_devices", "true", "-i", ""])
        return f"[{audio_idx}]" in text and "BlackHole" in text

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
        return True, "录制中（仅画面，ffmpeg 不可用或启动失败，已改用内置录制）"

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
