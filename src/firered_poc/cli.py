from __future__ import annotations

import argparse
import json

from .asr import build_asr
from .audio import float_to_int16, load_wav
from .config import AppConfig
from .pipeline import segment_audio


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="firered_poc")
    sub = parser.add_subparsers(dest="command", required=True)

    transcribe = sub.add_parser("transcribe", help="Transcribe a WAV file")
    transcribe.add_argument("--audio", required=True, help="Path to a WAV file")
    transcribe.add_argument("--config", default="configs/app.yaml", help="Path to app.yaml")
    transcribe.add_argument(
        "--vad",
        action="store_true",
        help="Segment the file with VAD before decoding (recommended for long audio)",
    )
    transcribe.add_argument("--json", action="store_true", help="Print JSON instead of plain text")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cfg = AppConfig.load(args.config)
    samples, sample_rate = load_wav(args.audio, cfg.audio.sample_rate)
    engine = build_asr(cfg.asr)

    items: list[dict] = []
    if args.vad:
        for segment in segment_audio(samples, sample_rate, cfg):
            result = engine.transcribe(segment.pcm, segment.sample_rate)
            if result.text:
                items.append(
                    {
                        "text": result.text,
                        "start_ms": segment.start_ms,
                        "end_ms": segment.end_ms,
                    }
                )
    else:
        result = engine.transcribe(float_to_int16(samples), sample_rate)
        if result.text:
            items.append(
                {
                    "text": result.text,
                    "start_ms": 0,
                    "end_ms": int(round(samples.size / sample_rate * 1000)),
                }
            )

    if args.json:
        print(json.dumps(items, ensure_ascii=False, indent=2))
    else:
        for item in items:
            print(item["text"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
