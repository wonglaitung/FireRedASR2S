from __future__ import annotations

import importlib.util
import json
import wave
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location(
    "validate_eval_data", ROOT / "scripts" / "validate_eval_data.py"
)
assert _SPEC and _SPEC.loader
_MODULE = importlib.util.module_from_spec(_SPEC)
assert isinstance(_MODULE, ModuleType)
_SPEC.loader.exec_module(_MODULE)

validate_dictation = _MODULE.validate_dictation
validate_meeting = _MODULE.validate_meeting


def write_wav(path: Path, frames: int = 3200, rate: int = 16000, channels: int = 1) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(channels)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(b"\x00\x00" * frames * channels)


def test_valid_dictation(tmp_path: Path) -> None:
    root = tmp_path / "dictation"
    write_wav(root / "audio" / "a.wav")
    write_wav(root / "audio" / "b.wav")
    rows = [
        {
            "id": "a",
            "audio": "audio/a.wav",
            "duration_s": 0.2,
            "sample_rate": 16000,
            "speaker_id": "spk1",
            "environment": "quiet",
            "device": "headset",
            "task": "email",
            "transcript": "我聽日同Alice開會",
            "split": "train",
        },
        {
            "id": "b",
            "audio": "audio/b.wav",
            "duration_s": 0.2,
            "sample_rate": 16000,
            "speaker_id": "spk2",
            "environment": "office",
            "device": "phone",
            "task": "notes",
            "transcript": "記得帶laptop",
            "split": "test",
        },
    ]
    (root / "manifest.json").write_text(json.dumps(rows), encoding="utf-8")
    issues, stats = validate_dictation(root)
    assert issues == []
    assert stats["clips"] == 2


def test_dictation_speaker_leakage(tmp_path: Path) -> None:
    root = tmp_path / "dictation"
    write_wav(root / "audio" / "a.wav")
    base = {
        "id": "a",
        "audio": "audio/a.wav",
        "duration_s": 0.2,
        "sample_rate": 16000,
        "speaker_id": "spk1",
        "environment": "quiet",
        "device": "headset",
        "task": "email",
        "transcript": "測試",
    }
    rows = [{**base, "id": "a", "split": "train"}, {**base, "id": "b", "split": "test"}]
    (root / "manifest.json").write_text(json.dumps(rows), encoding="utf-8")
    issues, _ = validate_dictation(root)
    assert any("multiple splits" in issue for issue in issues)


def test_meeting_validation(tmp_path: Path) -> None:
    root = tmp_path / "meeting"
    write_wav(root / "audio" / "m.wav")
    transcript = root / "transcripts" / "m.jsonl"
    transcript.parent.mkdir(parents=True)
    lines = [
        {
            "session_id": "m",
            "segment_id": "s1",
            "start_ms": 0,
            "end_ms": 100,
            "text": "我哋下個sprint做payment",
            "overlap": False,
        },
        {
            "session_id": "m",
            "segment_id": "s2",
            "start_ms": 100,
            "end_ms": 200,
            "text": "好",
            "overlap": True,
        },
    ]
    transcript.write_text(
        "\n".join(json.dumps(x, ensure_ascii=False) for x in lines), encoding="utf-8"
    )
    rows = [
        {
            "session_id": "m",
            "audio": "audio/m.wav",
            "transcript": "transcripts/m.jsonl",
            "duration_s": 0.2,
            "sample_rate": 16000,
            "participants": 3,
            "environment": "office",
            "device": "far_field",
            "split": "test",
        }
    ]
    (root / "manifest.json").write_text(json.dumps(rows), encoding="utf-8")
    issues, stats = validate_meeting(root)
    assert issues == []
    assert stats["segments"] == 2


def test_meeting_segment_beyond_audio(tmp_path: Path) -> None:
    root = tmp_path / "meeting"
    write_wav(root / "audio" / "m.wav")
    transcript = root / "transcripts" / "m.jsonl"
    transcript.parent.mkdir(parents=True)
    transcript.write_text(
        json.dumps(
            {"session_id": "m", "segment_id": "s1", "start_ms": 0, "end_ms": 9999, "text": "x"},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    rows = [
        {
            "session_id": "m",
            "audio": "audio/m.wav",
            "transcript": "transcripts/m.jsonl",
            "duration_s": 0.2,
            "participants": 3,
            "environment": "office",
            "device": "far_field",
            "split": "test",
        }
    ]
    (root / "manifest.json").write_text(json.dumps(rows), encoding="utf-8")
    issues, _ = validate_meeting(root)
    assert any("exceeds audio" in issue for issue in issues)
