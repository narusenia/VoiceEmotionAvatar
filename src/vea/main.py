"""VEA application entry point."""

import logging
import threading
import time
import sys

from vea.audio import AudioCapture
from vea.config import AppConfig
from vea.emotion import EmotionRecognizer
from vea.gui import VeaGui
from vea.osc_sender import OscSender
from vea.smoother import EmotionSmoother

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


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

    def _load_model(self) -> bool:
        try:
            self._gui.show_info("Loading model...")
            self._recognizer.load_model()
            self._gui.show_info("Model loaded")
            return True
        except Exception as e:
            logger.error("Failed to load model: %s", e)
            self._gui.show_error(f"モデルの読み込みに失敗しました:\n{e}")
            return False

    def _pipeline_loop(self) -> None:
        interval = self._config.emotion.analysis_interval_ms / 1000.0
        while self._pipeline_running:
            start = time.perf_counter()
            try:
                chunk = self._audio.get_chunk()
                rms = float((chunk ** 2).mean() ** 0.5)
                if rms < self._silence_threshold:
                    from vea.emotion import VEA_EMOTIONS
                    raw = {e: (1.0 if e == "neutral" else 0.0) for e in VEA_EMOTIONS}
                else:
                    raw = self._recognizer.predict(chunk, self._config.audio.sample_rate)
                smoothed = self._smoother.update(raw)
                self._osc.send(smoothed)
                self._gui.update_bars(smoothed)
            except Exception as e:
                logger.error("Pipeline error: %s", e)
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
        if not self._audio.start():
            self._gui.show_info("Waiting for microphone...")
        self._pipeline_running = True
        self._worker_thread = threading.Thread(target=self._pipeline_loop, daemon=True)
        self._worker_thread.start()

    def _stop_pipeline(self) -> None:
        self._pipeline_running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=2.0)
            self._worker_thread = None
        self._audio.stop()
        self._osc.close()
        self._smoother.reset()

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
        )
        self._gui.setup(
            default_device=self._config.audio.device,
            default_lerp=self._config.emotion.lerp_speed,
            default_hysteresis=self._config.emotion.hysteresis_threshold,
            default_silence=self._config.emotion.silence_threshold,
            default_osc_ip=self._config.osc.ip,
            default_osc_port=self._config.osc.port,
        )

        try:
            while self._gui.render_frame():
                self._gui.tick()
        except KeyboardInterrupt:
            pass
        finally:
            self._stop_pipeline()
            self._gui.teardown()


def main():
    app = VeaApp()
    app.run()


if __name__ == "__main__":
    main()
