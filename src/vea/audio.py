"""Audio capture module."""

from collections.abc import Callable
import logging
import threading
import time

import numpy as np
import sounddevice as sd

logger = logging.getLogger(__name__)

RETRY_INTERVAL = 3.0
MAX_RETRIES = 10
WINDOW_DURATION_S = 1.5


def list_input_devices() -> list[dict]:
    devices = sd.query_devices()
    return [
        {"index": i, "name": d["name"], "channels": d["max_input_channels"]}
        for i, d in enumerate(devices)
        if d["max_input_channels"] > 0
    ]


class AudioCapture:
    def __init__(
        self,
        device: int | None = None,
        sample_rate: int = 16000,
        channels: int = 1,
        chunk_duration_ms: int = 250,
    ):
        self._device = device
        self._sample_rate = sample_rate
        self._channels = channels
        self._chunk_samples = int(sample_rate * chunk_duration_ms / 1000)
        self._window_samples = int(sample_rate * WINDOW_DURATION_S)
        self._ring = np.zeros(self._window_samples, dtype=np.float32)
        self._write_pos = 0
        self._lock = threading.Lock()
        self._stream: sd.InputStream | None = None
        self._running = False
        self._on_error: Callable[[str], None] | None = None
        self._on_recovered: Callable[[], None] | None = None

    def set_device(self, device: int | None) -> None:
        self._device = device

    def set_error_callbacks(
        self,
        on_error: Callable[[str], None] | None = None,
        on_recovered: Callable[[], None] | None = None,
    ) -> None:
        self._on_error = on_error
        self._on_recovered = on_recovered

    def _audio_callback(self, indata, frames, time_info, status):
        if status:
            logger.warning("Audio status: %s", status)
        mono = indata[:, 0] if indata.ndim > 1 else indata.flatten()
        with self._lock:
            n = len(mono)
            if n >= self._window_samples:
                self._ring[:] = mono[-self._window_samples:]
                self._write_pos = 0
            else:
                end = self._write_pos + n
                if end <= self._window_samples:
                    self._ring[self._write_pos:end] = mono
                    self._write_pos = end % self._window_samples
                else:
                    first = self._window_samples - self._write_pos
                    self._ring[self._write_pos:] = mono[:first]
                    rest = n - first
                    self._ring[:rest] = mono[first:]
                    self._write_pos = rest

    def _open_stream(self) -> bool:
        try:
            self._stream = sd.InputStream(
                samplerate=self._sample_rate,
                channels=self._channels,
                dtype="float32",
                device=self._device,
                callback=self._audio_callback,
                blocksize=1024,
            )
            self._stream.start()
            return True
        except Exception as e:
            logger.error("Failed to open audio stream: %s", e)
            if self._on_error:
                self._on_error(f"マイクを開けません: {e}")
            return False

    def start(self) -> bool:
        self._running = True
        if self._open_stream():
            return True
        threading.Thread(target=self._retry_loop, daemon=True).start()
        return False

    def _retry_loop(self) -> None:
        for attempt in range(MAX_RETRIES):
            if not self._running:
                return
            time.sleep(RETRY_INTERVAL)
            logger.info("Retrying audio stream (attempt %d/%d)", attempt + 1, MAX_RETRIES)
            if self._open_stream():
                if self._on_recovered:
                    self._on_recovered()
                return
        logger.error("Failed to open audio stream after %d retries", MAX_RETRIES)
        if self._on_error:
            self._on_error(f"マイクに接続できません（{MAX_RETRIES}回リトライ失敗）")

    def get_chunk(self) -> np.ndarray:
        with self._lock:
            result = np.roll(self._ring, -self._write_pos)
        return result

    def stop(self) -> None:
        self._running = False
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
