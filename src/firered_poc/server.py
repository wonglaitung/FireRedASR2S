from __future__ import annotations

import argparse
import asyncio
import json
import uuid

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from .asr import ASRAdapter, build_asr
from .config import AppConfig
from .segmenter import Segment
from .session import Session, build_session


async def _send_segment(
    websocket: WebSocket,
    engine: ASRAdapter,
    segment: Segment,
    segment_id: int,
) -> None:
    try:
        result = await asyncio.to_thread(engine.transcribe, segment.pcm, segment.sample_rate)
    except Exception as exc:  # pragma: no cover - runtime failure path
        await websocket.send_json(
            {"type": "error", "code": "ASR_FAILED", "message": str(exc)}
        )
        return
    if not result.text:
        return
    await websocket.send_json(
        {
            "type": "final",
            "segment_id": segment_id,
            "text": result.text,
            "start_ms": segment.start_ms,
            "end_ms": segment.end_ms,
        }
    )


def create_app(config_path: str = "configs/app.yaml") -> FastAPI:
    cfg = AppConfig.load(config_path)
    engine = build_asr(cfg.asr)
    app = FastAPI(title="FireRedASR2S POC")

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok", "asr_backend": cfg.asr.backend}

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        await websocket.accept()
        session: Session | None = None
        session_id = uuid.uuid4().hex
        segment_id = 0

        try:
            while True:
                message = await websocket.receive()
                if message.get("type") == "websocket.disconnect":
                    break

                text = message.get("text")
                data = message.get("bytes")

                if text is not None:
                    payload = json.loads(text)
                    kind = payload.get("type")
                    if kind == "start":
                        session = build_session(cfg)
                        segment_id = 0
                        await websocket.send_json({"type": "ready", "session_id": session_id})
                    elif kind == "stop":
                        if session is not None:
                            for segment in session.flush():
                                segment_id += 1
                                await _send_segment(websocket, engine, segment, segment_id)
                        await websocket.send_json({"type": "stopped", "session_id": session_id})
                        break
                elif data is not None and session is not None:
                    for segment in session.push_pcm(data):
                        segment_id += 1
                        await _send_segment(websocket, engine, segment, segment_id)
        except WebSocketDisconnect:
            pass
        finally:
            session = None

    return app


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="firered_poc.server")
    parser.add_argument("--config", default="configs/app.yaml")
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=None)
    args = parser.parse_args(argv)

    cfg = AppConfig.load(args.config)
    host = args.host or cfg.server.host
    port = args.port or cfg.server.port
    uvicorn.run(create_app(args.config), host=host, port=port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
