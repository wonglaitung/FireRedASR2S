from __future__ import annotations

import asyncio
import json

import websockets

from firered_recorder.client import AsrStreamClient, RecorderConfig


def test_stream_client_protocol() -> None:
    received: list[tuple[str, object]] = []

    async def handler(ws) -> None:
        async for message in ws:
            if isinstance(message, bytes):
                received.append(("audio", len(message)))
                continue
            payload = json.loads(message)
            received.append((payload.get("type", "?"), payload))
            if payload.get("type") == "start":
                await ws.send(json.dumps({"type": "ready"}))
                await ws.send(
                    json.dumps(
                        {
                            "type": "final",
                            "segment_id": 1,
                            "text": "你好",
                            "start_ms": 0,
                            "end_ms": 500,
                        }
                    )
                )
            elif payload.get("type") == "stop":
                await ws.send(json.dumps({"type": "stopped"}))
                return

    async def run() -> list[dict]:
        server = await websockets.serve(handler, "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]
        events: list[dict] = []
        try:
            client = AsrStreamClient(
                RecorderConfig(url=f"ws://127.0.0.1:{port}/ws"),
                events.append,
            )
            task = asyncio.create_task(client.run())
            await asyncio.sleep(0.1)
            client.send(b"\x00\x00" * 320)
            client.stop()
            await asyncio.wait_for(task, timeout=5)
            return events
        finally:
            server.close()
            await server.wait_closed()

    events = asyncio.run(run())

    assert [event["type"] for event in events] == ["ready", "final", "stopped"]
    expected_start = {
        "type": "start",
        "sample_rate": 16000,
        "format": "pcm_s16le",
        "mode": "balanced",
        "lang": "auto",
        "output_script": "simplified",
    }
    assert ("start", expected_start) in received
    assert ("audio", 640) in received
    assert any(item[0] == "stop" for item in received)
