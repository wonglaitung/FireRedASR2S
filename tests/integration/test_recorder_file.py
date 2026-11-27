from __future__ import annotations

import asyncio
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

from firered_recorder.client import RecorderConfig
from firered_recorder.file_stream import stream_file

ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = ROOT / "models" / "sherpa-onnx-fire-red-asr2-zh_en-int8-2026-02-26"
MODEL = MODEL_DIR / "encoder.int8.onnx"
TEST_WAV = MODEL_DIR / "test_wavs" / "0.wav"

pytestmark = pytest.mark.skipif(not MODEL.exists(), reason="FireRedASR2 AED model not downloaded")


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def test_recorder_file_end_to_end() -> None:
    port = _free_port()
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "firered_poc.server",
            "--config",
            "configs/app.yaml",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    finals: list[dict] = []
    try:
        for _ in range(80):
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/health", timeout=1
                ) as response:
                    if response.status == 200:
                        break
            except Exception:
                time.sleep(0.5)
        else:
            pytest.fail("backend did not become healthy")

        asyncio.run(
            stream_file(
                RecorderConfig(url=f"ws://127.0.0.1:{port}/ws"),
                TEST_WAV,
                realtime=False,
                on_event=finals.append,
            )
        )
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()

    assert finals
    assert any(item.get("text") for item in finals)
