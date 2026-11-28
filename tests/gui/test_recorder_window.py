from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PyQt6")

from PyQt6.QtWidgets import QApplication  # noqa: E402

from firered_recorder.app import RecorderWindow  # noqa: E402
from firered_recorder.client import RecorderConfig  # noqa: E402
from firered_recorder.storage import TranscriptCsvWriter  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_window_smoke(app) -> None:
    window = RecorderWindow(RecorderConfig())
    try:
        assert "录音转写" in window.windowTitle()
        assert not window.windowIcon().isNull()
        assert window.record_btn.isEnabled()
        assert not window.stop_btn.isEnabled()

        window._append_final(
            {"type": "final", "text": "你好世界。", "start_ms": 0, "end_ms": 800}
        )
        assert "你好世界。" in window.transcript.toPlainText()
    finally:
        window.close()


def test_new_text_scrolls_to_bottom(app) -> None:
    window = RecorderWindow(RecorderConfig())
    try:
        window.show()
        app.processEvents()
        for index in range(40):
            window._append_final(
                {"type": "final", "text": f"第 {index} 行 " * 20, "start_ms": index * 1000}
            )
        app.processEvents()
        scrollbar = window.transcript.verticalScrollBar()
        assert scrollbar.maximum() > 0
        assert scrollbar.value() == scrollbar.maximum()
    finally:
        window.close()


def test_final_is_written_to_csv(app, tmp_path) -> None:
    import csv

    window = RecorderWindow(RecorderConfig())
    window._csv = TranscriptCsvWriter(tmp_path)
    path = window._csv.start()
    try:
        window._append_final(
            {"type": "final", "text": "我聽日同Alice開會", "start_ms": 1000, "end_ms": 2500}
        )
        window._csv.close()
        with path.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        assert rows[0]["text"] == "我聽日同Alice開會"
        assert rows[0]["start_ms"] == "1000"
    finally:
        window.close()
