from __future__ import annotations

import asyncio
import json
import queue
from collections.abc import Callable
from dataclasses import dataclass

import websockets

from .audio import SAMPLE_RATE

DEFAULT_URL = "ws://127.0.0.1:8000/ws"


@dataclass
class RecorderConfig:
    url: str = DEFAULT_URL
    mode: str = "balanced"
    lang: str = "auto"
    output_script: str = "simplified"


def start_message(cfg: RecorderConfig) -> dict:
    return {
        "type": "start",
        "sample_rate": SAMPLE_RATE,
        "format": "pcm_s16le",
        "mode": cfg.mode,
        "lang": cfg.lang,
        "output_script": cfg.output_script,
    }


class AsrStreamClient:
    """WebSocket client that streams PCM frames and surfaces server events."""

    def __init__(self, cfg: RecorderConfig, on_event: Callable[[dict], None]):
        self.cfg = cfg
        self.on_event = on_event
        self._outbox: queue.Queue[bytes | None] = queue.Queue()

    def send(self, pcm: bytes) -> None:
        self._outbox.put(pcm)

    def stop(self) -> None:
        self._outbox.put(None)

    async def run(self) -> None:
        async with websockets.connect(self.cfg.url, max_size=None, open_timeout=10) as ws:
            await ws.send(json.dumps(start_message(self.cfg)))
            sender = asyncio.create_task(self._send_loop(ws))
            try:
                async for raw in ws:
                    try:
                        event = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    self.on_event(event)
                    if event.get("type") == "stopped":
                        break
            finally:
                self._outbox.put(None)
                sender.cancel()
                await asyncio.gather(sender, return_exceptions=True)

    async def _send_loop(self, ws) -> None:
        while True:
            item = await asyncio.to_thread(self._outbox.get)
            if item is None:
                await ws.send(json.dumps({"type": "stop"}))
                return
            await ws.send(item)
