from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("httpx")
from fastapi.testclient import TestClient  # noqa: E402

from firered_poc.audio import float_to_int16, load_wav  # noqa: E402
from firered_poc.config import AppConfig  # noqa: E402
from firered_poc.server import create_app  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = ROOT / "models" / "sherpa-onnx-fire-red-asr2-ctc-zh_en-int8-2026-02-25"
MODEL = MODEL_DIR / "model.int8.onnx"
TEST_WAV = MODEL_DIR / "test_wavs" / "0.wav"

pytestmark = pytest.mark.skipif(not MODEL.exists(), reason="FireRedASR2 CTC model not downloaded")


def test_websocket_returns_final() -> None:
    cfg = AppConfig.load(ROOT / "configs" / "app.yaml")
    samples, sample_rate = load_wav(TEST_WAV, cfg.audio.sample_rate)
    pcm = float_to_int16(samples)

    app = create_app(str(ROOT / "configs" / "app.yaml"))
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            ws.send_json({"type": "start"})
            assert ws.receive_json()["type"] == "ready"

            for offset in range(0, len(pcm), 6400):
                ws.send_bytes(pcm[offset : offset + 6400])
            ws.send_json({"type": "stop"})

            finals = []
            while True:
                message = ws.receive_json()
                if message["type"] == "final":
                    finals.append(message)
                if message["type"] == "stopped":
                    break

    assert finals
    assert all(item["text"] for item in finals)
