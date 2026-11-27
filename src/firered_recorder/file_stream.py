from __future__ import annotations

import asyncio
from collections.abc import Callable
from pathlib import Path

from firered_poc.audio import float_to_int16, load_wav

from .audio import SAMPLE_RATE
from .client import AsrStreamClient, RecorderConfig


async def stream_file(
    cfg: RecorderConfig,
    wav_path: str | Path,
    realtime: bool = True,
    on_event: Callable[[dict], None] | None = None,
) -> list[dict]:
    """Stream a WAV file to the backend as 20ms PCM frames (headless test mode)."""
    samples, _ = load_wav(wav_path, SAMPLE_RATE)
    pcm = float_to_int16(samples)

    finals: list[dict] = []

    def handle(event: dict) -> None:
        if on_event is not None:
            on_event(event)
        if event.get("type") == "final":
            finals.append(event)

    client = AsrStreamClient(cfg, handle)
    task = asyncio.create_task(client.run())
    await asyncio.sleep(0.3)

    for offset in range(0, len(pcm), 640):
        client.send(pcm[offset : offset + 640])
        if realtime:
            await asyncio.sleep(0.02)

    client.stop()
    await task
    return finals
