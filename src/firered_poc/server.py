from __future__ import annotations

import argparse
import asyncio
import json
import socket
import uuid
from contextlib import asynccontextmanager, suppress

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from .asr import ASRAdapter, build_asr
from .config import AppConfig
from .postprocess import Postprocessor
from .segmenter import Segment
from .session import Session, build_session


async def _send_segment(
    websocket: WebSocket,
    engine: ASRAdapter,
    post: Postprocessor,
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
    text = post.process(result.text)
    if not text:
        return
    await websocket.send_json(
        {
            "type": "final",
            "segment_id": segment_id,
            "text": text,
            "start_ms": segment.start_ms,
            "end_ms": segment.end_ms,
        }
    )


def create_app(config_path: str = "configs/app.yaml") -> FastAPI:
    cfg = AppConfig.load(config_path)
    engine = build_asr(cfg.asr)
    post = Postprocessor(cfg.postprocess)
    active = {"connections": 0}

    async def _log_connections() -> None:
        interval = float(cfg.server.connection_log_interval_s)
        if interval <= 0:
            return
        while True:
            await asyncio.sleep(interval)
            print(
                f"[connections] active={active['connections']}",
                flush=True,
            )

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        task = asyncio.create_task(_log_connections())
        try:
            yield
        finally:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

    app = FastAPI(title="FireRedASR2S POC", lifespan=lifespan)

    @app.get("/health")
    async def health() -> dict:
        return {
            "status": "ok",
            "asr_backend": cfg.asr.backend,
            "active_connections": active["connections"],
        }

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        await websocket.accept()
        active["connections"] += 1
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
                                await _send_segment(
                                    websocket, engine, post, segment, segment_id
                                )
                        await websocket.send_json({"type": "stopped", "session_id": session_id})
                        break
                elif data is not None and session is not None:
                    for segment in session.push_pcm(data):
                        segment_id += 1
                        await _send_segment(websocket, engine, post, segment, segment_id)
        except WebSocketDisconnect:
            pass
        finally:
            session = None
            active["connections"] -= 1

    return app


def _lan_ipv4_addresses() -> list[str]:
    ips: set[str] = set()
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ips.add(info[4][0])
    except OSError:
        pass
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            ips.add(sock.getsockname()[0])
    except OSError:
        pass
    return sorted(ip for ip in ips if not ip.startswith("127.") and ip != "0.0.0.0")


def connection_urls(host: str, port: int) -> list[str]:
    if host in {"0.0.0.0", "::", ""}:
        urls = [f"ws://127.0.0.1:{port}/ws"]
        urls.extend(f"ws://{ip}:{port}/ws" for ip in _lan_ipv4_addresses())
        return list(dict.fromkeys(urls))
    return [f"ws://{host}:{port}/ws"]


def format_startup_banner(cfg: AppConfig, host: str, port: int) -> str:
    urls = connection_urls(host, port)
    health_urls = [url.replace("ws://", "http://").replace("/ws", "/health") for url in urls]
    lines = [
        "",
        "=" * 66,
        " FireRedASR2S ASR backend",
        f" ASR backend : {cfg.asr.backend}",
        f" VAD backend : {cfg.vad.backend}",
        f" Postprocess : punctuation={cfg.postprocess.punctuation} "
        f"itn={cfg.postprocess.itn} script={cfg.postprocess.output_script}",
        "",
        " WebSocket endpoints:",
        *[f"   {url}" for url in urls],
        "",
        " Health check:",
        *[f"   {url}" for url in health_urls],
        "",
        " Recorder (same machine / other machine):",
        *[f"   --url {url}" for url in urls],
        "=" * 66,
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="firered_poc.server")
    parser.add_argument("--config", default="configs/app.yaml")
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=None)
    args = parser.parse_args(argv)

    cfg = AppConfig.load(args.config)
    host = args.host or cfg.server.host
    port = args.port or cfg.server.port
    print(format_startup_banner(cfg, host, port), flush=True)
    uvicorn.run(create_app(args.config), host=host, port=port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
