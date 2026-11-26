from __future__ import annotations

from typing import Protocol

import numpy as np

from .audio import rms
from .config import VadConfig


class VAD(Protocol):
    def is_speech(self, frame: np.ndarray) -> bool: ...


class EnergyVAD:
    """Energy-based VAD for POC; replaceable with Silero VAD later."""

    def __init__(self, threshold: float = 0.02):
        self.threshold = threshold

    def is_speech(self, frame: np.ndarray) -> bool:
        return rms(frame) >= self.threshold


def make_vad(cfg: VadConfig) -> VAD:
    if cfg.backend == "energy":
        return EnergyVAD(cfg.energy_threshold)
    raise ValueError(f"unsupported VAD backend for POC: {cfg.backend}")
