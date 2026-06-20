"""Configuration management."""

from dataclasses import dataclass, field, asdict
from pathlib import Path

import yaml


CONFIG_DIR = Path.home() / ".vea"
CONFIG_PATH = CONFIG_DIR / "config.yaml"


@dataclass
class OscConfig:
    ip: str = "127.0.0.1"
    port: int = 9000


@dataclass
class EmotionConfig:
    analysis_interval_ms: int = 250
    lerp_speed: float = 0.15
    hysteresis_threshold: float = 0.1
    silence_threshold: float = 0.01
    parameter_prefix: str = "VEA"


@dataclass
class AudioConfig:
    device: int | None = None
    sample_rate: int = 16000
    channels: int = 1
    input_gain: float = 1.0


@dataclass
class AppConfig:
    audio: AudioConfig = field(default_factory=AudioConfig)
    emotion: EmotionConfig = field(default_factory=EmotionConfig)
    osc: OscConfig = field(default_factory=OscConfig)

    def save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            yaml.dump(asdict(self), f, default_flow_style=False, allow_unicode=True)

    @classmethod
    def load(cls) -> "AppConfig":
        if not CONFIG_PATH.exists():
            cfg = cls()
            cfg.save()
            return cfg
        with open(CONFIG_PATH, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return cls(
            audio=AudioConfig(**data.get("audio", {})),
            emotion=EmotionConfig(**data.get("emotion", {})),
            osc=OscConfig(**data.get("osc", {})),
        )
