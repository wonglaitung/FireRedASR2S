from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PyQt6")

from PyQt6.QtWidgets import QApplication  # noqa: E402

from firered_recorder.app import RecorderWindow  # noqa: E402
from firered_recorder.client import RecorderConfig  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_window_smoke(app) -> None:
    window = RecorderWindow(RecorderConfig())
    try:
        assert "录音转写" in window.windowTitle()
        assert window.record_btn.isEnabled()
        assert not window.stop_btn.isEnabled()

        window._append_final(
            {"type": "final", "text": "你好世界。", "start_ms": 0, "end_ms": 800}
        )
        assert "你好世界。" in window.transcript.toPlainText()
    finally:
        window.close()
