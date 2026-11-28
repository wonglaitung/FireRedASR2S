#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import wave
from collections import defaultdict
from pathlib import Path

SPLITS = {"train", "dev", "test"}


def read_wav(path: Path) -> tuple[int, int, int, float, str | None]:
    try:
        with wave.open(str(path), "rb") as handle:
            if handle.getcomptype() != "NONE":
                return 0, 0, 0, 0.0, "not PCM"
            rate = handle.getframerate()
            channels = handle.getnchannels()
            width = handle.getsampwidth()
            duration = handle.getnframes() / rate if rate else 0.0
            error = None
            if rate != 16000:
                error = f"sample_rate={rate}, expected 16000"
            elif channels != 1:
                error = f"channels={channels}, expected mono"
            elif width != 2:
                error = f"sample_width={width}, expected 16-bit"
            return rate, channels, width, duration, error
    except (OSError, wave.Error) as exc:
        return 0, 0, 0, 0.0, str(exc)


def load_manifest(root: Path) -> list[dict]:
    path = root / "manifest.json"
    if not path.exists():
        raise FileNotFoundError(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("manifest.json must be a JSON array")
    return data


def validate_dictation(root: Path) -> tuple[list[str], dict]:
    issues: list[str] = []
    rows = load_manifest(root)
    ids: set[str] = set()
    speaker_splits: dict[str, set[str]] = defaultdict(set)
    split_counts: dict[str, int] = defaultdict(int)
    total_duration = 0.0
    for index, row in enumerate(rows):
        prefix = f"dictation[{index}]"
        item_id = row.get("id")
        if not item_id:
            issues.append(f"{prefix}: missing id")
            continue
        if item_id in ids:
            issues.append(f"{prefix}: duplicate id {item_id}")
        ids.add(item_id)
        for key in ("audio", "transcript", "speaker_id", "environment", "device", "task", "split"):
            if not row.get(key):
                issues.append(f"{item_id}: missing {key}")
        split = row.get("split")
        if split not in SPLITS:
            issues.append(f"{item_id}: invalid split {split!r}")
        else:
            split_counts[split] += 1
        speaker = row.get("speaker_id")
        if speaker:
            speaker_splits[speaker].add(str(split))
        audio = root / str(row.get("audio", ""))
        if not audio.exists():
            issues.append(f"{item_id}: missing audio {audio}")
            continue
        _rate, _channels, _width, duration, wav_error = read_wav(audio)
        if wav_error:
            issues.append(f"{item_id}: {wav_error}")
        total_duration += duration
        declared = row.get("duration_s")
        if isinstance(declared, (int, float)) and abs(duration - float(declared)) > 0.05:
            issues.append(f"{item_id}: duration_s={declared} but wav={duration:.2f}")
        if row.get("sample_rate") not in (None, 16000):
            issues.append(f"{item_id}: manifest sample_rate is not 16000")
        if not str(row.get("transcript", "")).strip():
            issues.append(f"{item_id}: empty transcript")
    for speaker, splits in speaker_splits.items():
        if len(splits) > 1:
            issues.append(f"speaker {speaker} appears in multiple splits: {sorted(splits)}")
    stats = {
        "clips": len(rows),
        "duration_s": round(total_duration, 2),
        "splits": dict(split_counts),
        "speakers": len(speaker_splits),
    }
    return issues, stats


def validate_meeting(root: Path) -> tuple[list[str], dict]:
    issues: list[str] = []
    rows = load_manifest(root)
    session_ids: set[str] = set()
    split_counts: dict[str, int] = defaultdict(int)
    total_duration = 0.0
    total_segments = 0
    for index, row in enumerate(rows):
        prefix = f"meeting[{index}]"
        session_id = row.get("session_id")
        if not session_id:
            issues.append(f"{prefix}: missing session_id")
            continue
        if session_id in session_ids:
            issues.append(f"{prefix}: duplicate session_id {session_id}")
        session_ids.add(session_id)
        for key in ("audio", "transcript", "split", "participants", "environment", "device"):
            if not row.get(key):
                issues.append(f"{session_id}: missing {key}")
        split = row.get("split")
        if split not in SPLITS:
            issues.append(f"{session_id}: invalid split {split!r}")
        else:
            split_counts[split] += 1
        audio = root / str(row.get("audio", ""))
        if not audio.exists():
            issues.append(f"{session_id}: missing audio {audio}")
            continue
        _rate, _channels, _width, duration, wav_error = read_wav(audio)
        if wav_error:
            issues.append(f"{session_id}: {wav_error}")
        total_duration += duration
        declared = row.get("duration_s")
        if isinstance(declared, (int, float)) and abs(duration - float(declared)) > 0.05:
            issues.append(f"{session_id}: duration_s={declared} but wav={duration:.2f}")
        transcript = root / str(row.get("transcript", ""))
        if not transcript.exists():
            issues.append(f"{session_id}: missing transcript {transcript}")
            continue
        segment_ids: set[str] = set()
        previous_start = -1
        for line_no, line in enumerate(transcript.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            total_segments += 1
            try:
                segment = json.loads(line)
            except json.JSONDecodeError as exc:
                issues.append(f"{session_id}: transcript line {line_no}: {exc}")
                continue
            segment_id = segment.get("segment_id")
            if not segment_id:
                issues.append(f"{session_id}: transcript line {line_no}: missing segment_id")
            elif segment_id in segment_ids:
                issues.append(f"{session_id}: duplicate segment_id {segment_id}")
            segment_ids.add(segment_id)
            if segment.get("session_id") not in (None, session_id):
                issues.append(f"{session_id}: segment {segment_id} wrong session_id")
            start = segment.get("start_ms")
            end = segment.get("end_ms")
            if not isinstance(start, int) or not isinstance(end, int) or start < 0 or end <= start:
                issues.append(f"{session_id}: invalid timestamps at {segment_id}")
            else:
                if start < previous_start:
                    issues.append(f"{session_id}: segments not sorted at {segment_id}")
                previous_start = start
                if end > (duration * 1000 + 1):
                    issues.append(f"{session_id}: segment {segment_id} exceeds audio")
            if not str(segment.get("text", "")).strip():
                issues.append(f"{session_id}: empty text at {segment_id}")
    stats = {
        "sessions": len(rows),
        "duration_s": round(total_duration, 2),
        "splits": dict(split_counts),
        "segments": total_segments,
    }
    return issues, stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="validate_eval_data")
    parser.add_argument("--kind", required=True, choices=["dictation", "meeting"])
    parser.add_argument("--root", required=True)
    args = parser.parse_args(argv)
    root = Path(args.root)
    try:
        issues, stats = (
            validate_dictation(root) if args.kind == "dictation" else validate_meeting(root)
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 2
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    if issues:
        print(f"FAIL: {len(issues)} issue(s)")
        for issue in issues:
            print(f"  - {issue}")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
