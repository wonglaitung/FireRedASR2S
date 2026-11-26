from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class ASRResult:
    text: str
    start_ms: int = 0
    end_ms: int = 0
    confidence: float | None = None


class ASRAdapter(Protocol):
    def transcribe(self, pcm: bytes, sample_rate: int = 16000) -> ASRResult: ...
