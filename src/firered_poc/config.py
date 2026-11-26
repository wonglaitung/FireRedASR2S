from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class AudioConfig:
    sample_rate: int = 16000
    frame_ms: int = 20

    @property
    def frame_samples(self) -> int:
        return int(self.sample_rate * self.frame_ms / 1000)


@dataclass
class VadConfig:
    backend: str = "energy"
    energy_threshold: float = 0.02
    pre_roll_ms: int = 300
    post_roll_ms: int = 300
    max_end_silence_ms: int = 450
    min_speech_ms: int = 250
    hard_max_segment_ms: int = 15000
    merge_gap_ms: int = 1200


@dataclass
class AsrConfig:
    backend: str = "firered_ctc"
    model: str = ""
    tokens: str = ""
    encoder: str = ""
    decoder: str = ""
    num_threads: int = 2
    provider: str = "cpu"


@dataclass
class ServerConfig:
    host: str = "0.0.0.0"
    port: int = 8000


def _build(cls: type, data: dict | None):
    if not data:
        return cls()
    names = {f.name for f in dataclasses.fields(cls)}
    return cls(**{k: v for k, v in data.items() if k in names})


@dataclass
class AppConfig:
    audio: AudioConfig = field(default_factory=AudioConfig)
    vad: VadConfig = field(default_factory=VadConfig)
    asr: AsrConfig = field(default_factory=AsrConfig)
    server: ServerConfig = field(default_factory=ServerConfig)

    @classmethod
    def load(cls, path: str | Path) -> AppConfig:
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        return cls(
            audio=_build(AudioConfig, raw.get("audio")),
            vad=_build(VadConfig, raw.get("vad")),
            asr=_build(AsrConfig, raw.get("asr")),
            server=_build(ServerConfig, raw.get("server")),
        )
