from __future__ import annotations

import csv
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

CSV_FIELDS = ["start_ms", "end_ms", "text"]


def recorder_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def default_transcript_dir() -> Path:
    override = os.environ.get("FIRERED_RECORDER_DATA_DIR")
    if override:
        return Path(override).expanduser()
    return recorder_dir() / "transcripts"


class TranscriptCsvWriter:
    """Append one CSV row per final segment and flush immediately."""

    def __init__(self, directory: str | Path | None = None):
        self.directory = Path(directory) if directory else default_transcript_dir()
        self.path: Path | None = None
        self.session_id: str = ""
        self._file = None
        self._writer: csv.DictWriter | None = None

    def start(self) -> Path:
        self.close()
        self.directory.mkdir(parents=True, exist_ok=True)
        now = datetime.now().astimezone()
        self.session_id = f"{now:%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:6]}"
        self.path = self.directory / f"recorder-{self.session_id}.csv"
        self._file = self.path.open("w", newline="", encoding="utf-8-sig")
        self._writer = csv.DictWriter(self._file, fieldnames=CSV_FIELDS)
        self._writer.writeheader()
        self._file.flush()
        return self.path

    def write(self, start_ms: int, end_ms: int, text: str) -> None:
        if self._writer is None or self._file is None:
            return
        self._writer.writerow(
            {"start_ms": start_ms, "end_ms": end_ms, "text": text}
        )
        self._file.flush()

    def close(self) -> None:
        if self._file is not None:
            self._file.flush()
            self._file.close()
        self._file = None
        self._writer = None

    @property
    def active(self) -> bool:
        return self._file is not None
