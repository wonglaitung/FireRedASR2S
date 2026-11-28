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
    silero_model: str = ""
    silero_threshold: float = 0.5
    silero_min_silence_ms: int = 500
    silero_min_speech_ms: int = 250
    silero_max_speech_ms: int = 20000
    silero_window_size: int = 512


@dataclass
class PostprocessConfig:
    punctuation: bool = False
    punctuation_model: str = ""
    itn: bool = False
    output_script: str = "as-is"  # as-is | simplified | traditional


@dataclass
class AsrConfig:
    backend: str = "firered_aed"
    tokens: str = ""
    encoder: str = ""
    decoder: str = ""
    num_threads: int = 2
    provider: str = "cpu"
    # Official PyTorch AED (optional, separate from the sherpa-onnx path)
    model_dir: str = ""
    repo_path: str = ""
    use_gpu: bool = False
    use_half: bool = False
    beam_size: int = 5
    nbest: int = 1
    decode_max_len: int = 0
    softmax_smoothing: float = 1.25
    aed_length_penalty: float = 0.6
    eos_penalty: float = 1.0
    elm_dir: str = ""
    elm_weight: float = 0.0


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
    postprocess: PostprocessConfig = field(default_factory=PostprocessConfig)
    server: ServerConfig = field(default_factory=ServerConfig)

    @classmethod
    def load(cls, path: str | Path) -> AppConfig:
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        return cls(
            audio=_build(AudioConfig, raw.get("audio")),
            vad=_build(VadConfig, raw.get("vad")),
            asr=_build(AsrConfig, raw.get("asr")),
            postprocess=_build(PostprocessConfig, raw.get("postprocess")),
            server=_build(ServerConfig, raw.get("server")),
        )
