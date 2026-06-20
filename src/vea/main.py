"""VEA application entry point."""

import logging
import threading
import time
import sys

import numpy as np

from vea.audio import AudioCapture
from vea.config import AppConfig
from vea.emotion import EmotionRecognizer, neutral_scores, get_emotions
from vea.gui import VeaGui
from vea.osc_sender import OscSender
from vea.smoother import EmotionSmoother

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def _print_banner():
    print("=" * 50)
    print("  VoiceEmotionAvatar (VEA)")
    print("  Voice → Emotion → OSC → VRChat")
    print("=" * 50)
    print()


class VeaApp:
    def __init__(self):
        self._config = AppConfig.load()
        self._audio = AudioCapture(
            device=self._config.audio.device,
            sample_rate=self._config.audio.sample_rate,
            channels=self._config.audio.channels,
            chunk_duration_ms=self._config.emotion.analysis_interval_ms,
        )
        self._recognizer = EmotionRecognizer()
        self._smoother = EmotionSmoother(
            lerp_speed=self._config.emotion.lerp_speed,
            hysteresis_threshold=self._config.emotion.hysteresis_threshold,
        )
        self._osc = OscSender(
            ip=self._config.osc.ip,
            port=self._config.osc.port,
            prefix=self._config.emotion.parameter_prefix,
        )
        self._gui = VeaGui()
        self._worker_thread: threading.Thread | None = None
        self._pipeline_running = False
        self._silence_threshold = self._config.emotion.silence_threshold
        self._input_gain = self._config.audio.input_gain
        self._log_counter = 0
        self._latest_rms = 0.0

    def _load_model(self) -> bool:
        if self._recognizer._model is not None:
            return True
        try:
            self._gui.show_info("Loading model...")
            logger.info("モデルロード開始...")
            self._recognizer.load_model()
            self._gui.show_info("Model loaded - Ready!")
            logger.info("準備完了！")
            return True
        except Exception as e:
            logger.error("モデルロード失敗: %s", e)
            self._gui.show_error(f"モデルの読み込みに失敗しました:\n{e}")
            return False

    def _inference_loop(self) -> None:
        interval = self._config.emotion.analysis_interval_ms / 1000.0
        while self._pipeline_running:
            start = time.perf_counter()
            try:
                chunk = self._audio.get_chunk()
                chunk = chunk * self._input_gain
                chunk = np.clip(chunk, -1.0, 1.0)

                rms = float((chunk ** 2).mean() ** 0.5)
                self._latest_rms = rms

                if rms < self._silence_threshold:
                    raw = neutral_scores(self._recognizer.full_mode)
                    is_silent = True
                else:
                    raw = self._recognizer.predict(chunk, self._config.audio.sample_rate)
                    is_silent = False

                self._smoother.set_target(raw)

                self._log_counter += 1
                if self._log_counter % 4 == 0 and not is_silent:
                    dominant = max(raw, key=raw.get)
                    raw_str = " ".join(f"{k}={v:.2f}" for k, v in raw.items())
                    logger.info(
                        "RMS=%.4f | raw: %s [%s]",
                        rms, raw_str, dominant,
                    )

            except Exception as e:
                logger.error("Inference error: %s", e)
            elapsed = time.perf_counter() - start
            sleep_time = max(0, interval - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)

    def _start_pipeline(self) -> None:
        if self._pipeline_running:
            return
        if not self._load_model():
            return
        self._osc.connect()
        logger.info("OSC接続: %s:%d", self._config.osc.ip, self._config.osc.port)
        if not self._audio.start():
            self._gui.show_info("Waiting for microphone...")
            logger.info("マイク接続待ち...")
        else:
            logger.info("マイク接続OK")
        self._pipeline_running = True
        self._worker_thread = threading.Thread(target=self._inference_loop, daemon=True)
        self._worker_thread.start()
        logger.info("パイプライン開始 (推論=%.0fms, 出力=毎フレーム)", self._config.emotion.analysis_interval_ms)

    def _stop_pipeline(self) -> None:
        self._pipeline_running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=2.0)
            self._worker_thread = None
        self._audio.stop()
        self._osc.close()
        self._smoother.reset()
        logger.info("パイプライン停止")

    def _on_device_change(self, device_id: int | None) -> None:
        self._config.audio.device = device_id
        self._audio.set_device(device_id)
        self._config.save()

    def _on_lerp_change(self, value: float) -> None:
        self._smoother.set_lerp_speed(value)
        self._config.emotion.lerp_speed = value
        self._config.save()

    def _on_hysteresis_change(self, value: float) -> None:
        self._smoother.set_hysteresis(value)
        self._config.emotion.hysteresis_threshold = value
        self._config.save()

    def _on_silence_change(self, value: float) -> None:
        self._silence_threshold = value
        self._config.emotion.silence_threshold = value
        self._config.save()

    def _on_gain_change(self, value: float) -> None:
        self._input_gain = value
        self._config.audio.input_gain = value
        self._config.save()
        logger.info("Input Gain: %.1f", value)

    def _on_instant_mode_change(self, enabled: bool) -> None:
        self._smoother.set_instant_mode(enabled)
        logger.info("Instant Mode: %s", "ON" if enabled else "OFF")

    def _on_instant_threshold_change(self, value: float) -> None:
        self._smoother.set_instant_threshold(value)

    def _on_instant_smoothing_change(self, value: float) -> None:
        self._smoother.set_instant_smoothing(value)

    def _on_hold_change(self, value: float) -> None:
        self._smoother.set_hold_time(value)

    def _on_full_mode_change(self, enabled: bool) -> None:
        self._recognizer.full_mode = enabled
        self._smoother.set_full_mode(enabled)
        logger.info("Emotion Mode: %s", "Full (7)" if enabled else "Simple (5)")

    def _on_osc_change(self, ip: str, port: int) -> None:
        self._osc.update_target(ip, port)
        self._config.osc.ip = ip
        self._config.osc.port = port
        self._config.save()

    def run(self) -> None:
        self._audio.set_error_callbacks(
            on_error=lambda msg: self._gui.show_error(msg),
            on_recovered=lambda: self._gui.show_info("Microphone reconnected"),
        )
        self._gui.set_callbacks(
            on_device_change=self._on_device_change,
            on_start=self._start_pipeline,
            on_stop=self._stop_pipeline,
            on_lerp_change=self._on_lerp_change,
            on_hysteresis_change=self._on_hysteresis_change,
            on_osc_change=self._on_osc_change,
            on_silence_change=self._on_silence_change,
            on_gain_change=self._on_gain_change,
            on_instant_mode_change=self._on_instant_mode_change,
            on_instant_threshold_change=self._on_instant_threshold_change,
            on_instant_smoothing_change=self._on_instant_smoothing_change,
            on_hold_change=self._on_hold_change,
            on_full_mode_change=self._on_full_mode_change,
        )
        self._gui.setup(
            default_device=self._config.audio.device,
            default_lerp=self._config.emotion.lerp_speed,
            default_hysteresis=self._config.emotion.hysteresis_threshold,
            default_silence=self._config.emotion.silence_threshold,
            default_gain=self._config.audio.input_gain,
            default_osc_ip=self._config.osc.ip,
            default_osc_port=self._config.osc.port,
        )

        try:
            while self._gui.render_frame():
                if self._pipeline_running:
                    smoothed = self._smoother.tick()
                    self._osc.send(smoothed)
                    self._gui.update_bars(smoothed)
                    self._gui.update_volume(self._latest_rms)
                self._gui.tick()
        except KeyboardInterrupt:
            pass
        finally:
            self._stop_pipeline()
            self._gui.teardown()


def main():
    _print_banner()
    logger.info("設定ファイル読み込み中...")
    app = VeaApp()
    logger.info("GUI起動中...")
    app.run()


if __name__ == "__main__":
    main()
