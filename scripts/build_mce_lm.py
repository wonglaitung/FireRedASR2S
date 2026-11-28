#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
import urllib.request
from pathlib import Path

from firered_poc.lm import MixedNgramLM

ROOT = Path(__file__).resolve().parents[1]
DATASET = "AlienKevin%2Fmixed_cantonese_and_english_speech"
ROWS_URL = (
    "https://datasets-server.huggingface.co/rows"
    f"?dataset={DATASET}&config=default&split=train"
)


def fetch_rows(cache: Path, max_rows: int) -> list[dict]:
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    rows: list[dict] = []
    for offset in range(0, max_rows, 100):
        url = f"{ROWS_URL}&offset={offset}&length=100"
        for attempt in range(6):
            try:
                with urllib.request.urlopen(url, timeout=60) as response:
                    payload = json.load(response)
                break
            except Exception as exc:
                print(f"retry offset={offset} attempt={attempt + 1}: {exc}")
                time.sleep(2 + attempt * 2)
        else:
            print(f"stopping at offset={offset}; keeping {len(rows)} rows")
            break
        for item in payload["rows"]:
            row = item["row"]
            rows.append(
                {
                    "index": item["row_idx"],
                    "sentence": row["sentence"],
                    "topic": row.get("topic", ""),
                }
            )
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
        print(f"fetched {len(rows)} rows")
        time.sleep(0.5)
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="build_mce_lm")
    parser.add_argument("--cache", default=str(ROOT / "models" / "mce_text_cache.json"))
    parser.add_argument("--output", default=str(ROOT / "models" / "mce_lm.json"))
    parser.add_argument("--eval-manifest", default=str(ROOT / "eval" / "yue_en" / "manifest.json"))
    parser.add_argument("--max-rows", type=int, default=2500)
    args = parser.parse_args(argv)

    rows = fetch_rows(Path(args.cache), args.max_rows)
    eval_rows = json.loads(Path(args.eval_manifest).read_text(encoding="utf-8"))
    excluded = {row["source_index"] for row in eval_rows}
    train = [row["sentence"] for row in rows if row["index"] not in excluded]
    lm = MixedNgramLM.train(train)
    lm.save(args.output)
    print(f"trained on {len(train)} sentences ({lm.vocab_size} tokens), wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
