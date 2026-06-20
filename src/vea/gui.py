"""Dear PyGui GUI module."""

from collections.abc import Callable
import logging

import dearpygui.dearpygui as dpg

from vea.audio import list_input_devices
from vea.emotion import VEA_EMOTIONS

logger = logging.getLogger(__name__)

EMOTION_COLORS = {
    "joy": (255, 220, 50),
    "anger": (220, 50, 50),
    "sadness": (80, 120, 220),
    "surprise": (255, 160, 30),
    "neutral": (160, 160, 160),
}

EMOTION_LABELS_JA = {
    "joy": "Joy / 喜び",
    "anger": "Anger / 怒り",
    "sadness": "Sadness / 悲しみ",
    "surprise": "Surprise / 驚き",
    "neutral": "Neutral / ニュートラル",
}


class VeaGui:
    def __init__(self):
        self._bars: dict[str, int] = {}
        self._volume_bar: int | None = None
        self._volume_text: int | None = None
        self._status_text: int | None = None
        self._on_device_change: Callable[[int | None], None] | None = None
        self._on_start: Callable[[], None] | None = None
        self._on_stop: Callable[[], None] | None = None
        self._on_lerp_change: Callable[[float], None] | None = None
        self._on_hysteresis_change: Callable[[float], None] | None = None
        self._on_osc_change: Callable[[str, int], None] | None = None
        self._on_silence_change: Callable[[float], None] | None = None
        self._on_gain_change: Callable[[float], None] | None = None
        self._on_instant_mode_change: Callable[[bool], None] | None = None
        self._on_instant_threshold_change: Callable[[float], None] | None = None
        self._on_instant_smoothing_change: Callable[[float], None] | None = None
        self._running = False
        self._devices: list[dict] = []

    def set_callbacks(
        self,
        on_device_change: Callable[[int | None], None] | None = None,
        on_start: Callable[[], None] | None = None,
        on_stop: Callable[[], None] | None = None,
        on_lerp_change: Callable[[float], None] | None = None,
        on_hysteresis_change: Callable[[float], None] | None = None,
        on_osc_change: Callable[[str, int], None] | None = None,
        on_silence_change: Callable[[float], None] | None = None,
        on_gain_change: Callable[[float], None] | None = None,
        on_instant_mode_change: Callable[[bool], None] | None = None,
        on_instant_threshold_change: Callable[[float], None] | None = None,
        on_instant_smoothing_change: Callable[[float], None] | None = None,
    ) -> None:
        self._on_device_change = on_device_change
        self._on_start = on_start
        self._on_stop = on_stop
        self._on_lerp_change = on_lerp_change
        self._on_hysteresis_change = on_hysteresis_change
        self._on_osc_change = on_osc_change
        self._on_silence_change = on_silence_change
        self._on_gain_change = on_gain_change
        self._on_instant_mode_change = on_instant_mode_change
        self._on_instant_threshold_change = on_instant_threshold_change
        self._on_instant_smoothing_change = on_instant_smoothing_change

    def _build_ui(
        self,
        default_device: int | None,
        default_lerp: float,
        default_hysteresis: float,
        default_silence: float,
        default_gain: float,
        default_osc_ip: str,
        default_osc_port: int,
    ) -> None:
        self._devices = list_input_devices()
        device_names = [d["name"] for d in self._devices]
        default_idx = 0
        if default_device is not None:
            for i, d in enumerate(self._devices):
                if d["index"] == default_device:
                    default_idx = i
                    break

        with dpg.window(label="VoiceEmotionAvatar", tag="main_window"):
            dpg.add_text("VoiceEmotionAvatar (VEA)", color=(200, 200, 255))
            dpg.add_separator()

            dpg.add_text("Microphone")
            dpg.add_combo(
                items=device_names,
                default_value=device_names[default_idx] if device_names else "",
                callback=self._on_device_selected,
                tag="device_combo",
                width=-1,
            )

            # Input Gain
            dpg.add_slider_float(
                label="Input Gain",
                default_value=default_gain,
                min_value=0.1,
                max_value=10.0,
                callback=self._on_gain_slider,
                width=200,
                tag="gain_slider",
            )

            # Volume Meter
            with dpg.group(horizontal=True):
                dpg.add_text("Level: ")
                self._volume_bar = dpg.add_progress_bar(
                    default_value=0.0,
                    overlay="--",
                    width=-80,
                    tag="volume_bar",
                )
                self._volume_text = dpg.add_text("0.000", tag="volume_text")
            dpg.bind_item_theme(self._volume_bar, self._create_bar_theme((50, 200, 50)))

            dpg.add_separator()

            with dpg.group(horizontal=True):
                dpg.add_button(label="Start", callback=self._on_start_clicked, tag="start_btn")
                dpg.add_button(
                    label="Stop", callback=self._on_stop_clicked, tag="stop_btn", enabled=False,
                )

            self._status_text = dpg.add_text("Stopped", color=(200, 200, 200), tag="status_text")
            dpg.add_separator()

            dpg.add_text("Emotion Monitor")
            for emotion in VEA_EMOTIONS:
                color = EMOTION_COLORS[emotion]
                label = EMOTION_LABELS_JA[emotion]
                with dpg.group(horizontal=True):
                    dpg.add_text(f"{label:24s}")
                    bar = dpg.add_progress_bar(
                        default_value=0.0,
                        overlay="0.0%",
                        width=-1,
                    )
                    dpg.bind_item_theme(bar, self._create_bar_theme(color))
                    self._bars[emotion] = bar

            dpg.add_separator()
            dpg.add_text("Mode")

            dpg.add_checkbox(
                label="Instant Mode (閾値超えで即時切替)",
                default_value=False,
                callback=self._on_instant_toggle,
                tag="instant_mode_cb",
            )
            dpg.add_slider_float(
                label="Instant Threshold",
                default_value=0.4,
                min_value=0.1,
                max_value=0.9,
                callback=self._on_instant_threshold_slider,
                width=200,
                tag="instant_threshold_slider",
            )
            dpg.add_slider_float(
                label="Smoothing",
                default_value=0.5,
                min_value=0.05,
                max_value=1.0,
                callback=self._on_instant_smoothing_slider,
                width=200,
                tag="instant_smoothing_slider",
            )

            dpg.add_separator()
            dpg.add_text("Settings")

            dpg.add_slider_float(
                label="Lerp Speed",
                default_value=default_lerp,
                min_value=0.01,
                max_value=1.0,
                callback=self._on_lerp_slider,
                width=200,
                tag="lerp_slider",
            )
            dpg.add_slider_float(
                label="Hysteresis",
                default_value=default_hysteresis,
                min_value=0.0,
                max_value=0.5,
                callback=self._on_hysteresis_slider,
                width=200,
                tag="hysteresis_slider",
            )
            dpg.add_slider_float(
                label="Silence Threshold",
                default_value=default_silence,
                min_value=0.001,
                max_value=0.1,
                format="%.3f",
                callback=self._on_silence_slider,
                width=200,
            )

            dpg.add_separator()
            if dpg.add_collapsing_header(label="Advanced Settings"):
                dpg.add_input_text(
                    label="OSC IP",
                    default_value=default_osc_ip,
                    tag="osc_ip_input",
                    width=200,
                )
                dpg.add_input_int(
                    label="OSC Port",
                    default_value=default_osc_port,
                    tag="osc_port_input",
                    width=200,
                )
                dpg.add_button(label="Apply OSC Settings", callback=self._on_osc_apply)

    def _create_bar_theme(self, color: tuple[int, int, int]) -> int:
        with dpg.theme() as theme:
            with dpg.theme_component(dpg.mvProgressBar):
                dpg.add_theme_color(dpg.mvThemeCol_PlotHistogram, color)
        return theme

    def _on_device_selected(self, sender, value, user_data) -> None:
        for d in self._devices:
            if d["name"] == value:
                if self._on_device_change:
                    self._on_device_change(d["index"])
                return

    def _on_start_clicked(self, sender, value, user_data) -> None:
        if self._on_start:
            self._on_start()
        self._running = True
        dpg.configure_item("start_btn", enabled=False)
        dpg.configure_item("stop_btn", enabled=True)
        dpg.set_value("status_text", "Running")
        dpg.configure_item("status_text", color=(50, 220, 50))

    def _on_stop_clicked(self, sender, value, user_data) -> None:
        if self._on_stop:
            self._on_stop()
        self._running = False
        dpg.configure_item("start_btn", enabled=True)
        dpg.configure_item("stop_btn", enabled=False)
        dpg.set_value("status_text", "Stopped")
        dpg.configure_item("status_text", color=(200, 200, 200))

    def _on_lerp_slider(self, sender, value, user_data) -> None:
        if self._on_lerp_change:
            self._on_lerp_change(value)

    def _on_hysteresis_slider(self, sender, value, user_data) -> None:
        if self._on_hysteresis_change:
            self._on_hysteresis_change(value)

    def _on_silence_slider(self, sender, value, user_data) -> None:
        if self._on_silence_change:
            self._on_silence_change(value)

    def _on_gain_slider(self, sender, value, user_data) -> None:
        if self._on_gain_change:
            self._on_gain_change(value)

    def _on_instant_toggle(self, sender, value, user_data) -> None:
        if self._on_instant_mode_change:
            self._on_instant_mode_change(value)

    def _on_instant_threshold_slider(self, sender, value, user_data) -> None:
        if self._on_instant_threshold_change:
            self._on_instant_threshold_change(value)

    def _on_instant_smoothing_slider(self, sender, value, user_data) -> None:
        if self._on_instant_smoothing_change:
            self._on_instant_smoothing_change(value)

    def _on_osc_apply(self, sender, value, user_data) -> None:
        ip = dpg.get_value("osc_ip_input")
        port = dpg.get_value("osc_port_input")
        if self._on_osc_change:
            self._on_osc_change(ip, port)

    def update_bars(self, scores: dict[str, float]) -> None:
        for emotion, bar_id in self._bars.items():
            val = scores.get(emotion, 0.0)
            dpg.set_value(bar_id, val)
            dpg.configure_item(bar_id, overlay=f"{val:.1%}")

    def update_volume(self, rms: float) -> None:
        display = min(rms * 5.0, 1.0)
        dpg.set_value("volume_bar", display)
        dpg.set_value("volume_text", f"{rms:.3f}")
        if rms > 0.05:
            color = (50, 220, 50)
        elif rms > 0.01:
            color = (220, 220, 50)
        else:
            color = (100, 100, 100)
        dpg.configure_item("volume_bar", overlay=f"{rms:.3f}")

    def show_error(self, message: str) -> None:
        with dpg.window(label="Error", modal=True, no_close=False, width=400, height=120):
            dpg.add_text(message, wrap=380)
            dpg.add_button(label="OK", callback=lambda: dpg.delete_item(dpg.last_container()))

    def show_info(self, message: str) -> None:
        dpg.set_value("status_text", message)

    def setup(
        self,
        default_device: int | None = None,
        default_lerp: float = 0.15,
        default_hysteresis: float = 0.1,
        default_silence: float = 0.01,
        default_gain: float = 1.0,
        default_osc_ip: str = "127.0.0.1",
        default_osc_port: int = 9000,
    ) -> None:
        dpg.create_context()
        dpg.create_viewport(title="VoiceEmotionAvatar", width=500, height=680)
        self._build_ui(
            default_device, default_lerp, default_hysteresis,
            default_silence, default_gain, default_osc_ip, default_osc_port,
        )
        dpg.setup_dearpygui()
        dpg.set_primary_window("main_window", True)
        dpg.show_viewport()

    def render_frame(self) -> bool:
        return dpg.is_dearpygui_running()

    def tick(self) -> None:
        dpg.render_dearpygui_frame()

    def teardown(self) -> None:
        dpg.destroy_context()
