#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from firered_poc.asr import build_asr
from firered_poc.audio import float_to_int16, load_wav
from firered_poc.config import AppConfig
from firered_poc.postprocess import Postprocessor

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "eval" / "yue_en" / "manifest.json"


def english_terms(text: str) -> list[str]:
    return [t for t in re.findall(r"[A-Za-z][A-Za-z0-9.'\-]*", text) if len(t) >= 2]


def matched_terms(text: str, terms: list[str]) -> list[str]:
    low = text.lower()
    return [term for term in terms if term.lower() in low]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="eval_yue_en")
    parser.add_argument("--config", default="configs/app.yaml")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--output", default="")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cfg = AppConfig.load(args.config)
    engine = build_asr(cfg.asr)
    post = Postprocessor(cfg.postprocess)
    manifest_path = Path(args.manifest)
    rows = json.loads(manifest_path.read_text(encoding="utf-8"))

    results = []
    total_terms = 0
    total_hits = 0
    for row in rows:
        wav = manifest_path.parent / row["audio"]
        samples, sr = load_wav(wav, cfg.audio.sample_rate)
        text = post.process(engine.transcribe(float_to_int16(samples), sr).text)
        terms = english_terms(row["transcript"])
        hits = matched_terms(text, terms)
        total_terms += len(terms)
        total_hits += len(hits)
        results.append(
            {
                "id": row["id"],
                "topic": row["topic"],
                "duration_s": row["duration_s"],
                "reference": row["transcript"],
                "english_terms": terms,
                "text": text,
                "hits": hits,
                "recall": f"{len(hits)}/{len(terms)}",
            }
        )
        print(f"{row['id']} {row['topic']}: {len(hits)}/{len(terms)}")

    recall = total_hits / total_terms if total_terms else 0.0
    print(f"TOTAL {total_hits}/{total_terms} = {recall:.1%}")

    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
