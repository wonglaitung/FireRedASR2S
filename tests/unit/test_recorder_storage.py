from __future__ import annotations

import csv
from pathlib import Path

from firered_recorder.storage import CSV_FIELDS, TranscriptCsvWriter, default_transcript_dir


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_writer_persists_final_rows(tmp_path: Path) -> None:
    writer = TranscriptCsvWriter(tmp_path)
    path = writer.start()
    writer.write(1000, 2500, "我聽日同Alice開會")
    writer.write(3000, 4200, "記得帶laptop")
    writer.close()

    rows = read_csv(path)
    assert [row["text"] for row in rows] == ["我聽日同Alice開會", "記得帶laptop"]
    assert rows[0]["start_ms"] == "1000"
    assert rows[0]["end_ms"] == "2500"
    assert set(rows[0]) == set(CSV_FIELDS)


def test_writer_creates_a_new_session_file(tmp_path: Path) -> None:
    writer = TranscriptCsvWriter(tmp_path)
    first = writer.start()
    writer.write(0, 100, "第一句")
    second = writer.start()
    writer.write(0, 100, "第二句")
    writer.close()

    assert first != second
    assert read_csv(first)[0]["text"] == "第一句"
    assert read_csv(second)[0]["text"] == "第二句"


def test_default_transcript_dir_can_be_overridden(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("FIRERED_RECORDER_DATA_DIR", str(tmp_path))
    assert default_transcript_dir() == tmp_path
