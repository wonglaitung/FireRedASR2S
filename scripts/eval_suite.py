#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from opencc import OpenCC

from firered_poc.asr import build_asr
from firered_poc.audio import float_to_int16, load_wav
from firered_poc.config import AppConfig
from firered_poc.postprocess import Postprocessor

ROOT = Path(__file__).resolve().parents[1]
_T2S = OpenCC("t2s")
_EN_RE = re.compile(r"[A-Za-z][A-Za-z0-9.'\-]*")
_EN_TOKEN_RE = re.compile(r"[a-z0-9']+")


def levenshtein(ref: list[str], hyp: list[str]) -> int:
    previous = list(range(len(hyp) + 1))
    for i, ref_item in enumerate(ref, 1):
        current = [i]
        for j, hyp_item in enumerate(hyp, 1):
            insert = current[j - 1] + 1
            delete = previous[j] + 1
            substitute = previous[j - 1] + (ref_item != hyp_item)
            current.append(min(insert, delete, substitute))
        previous = current
    return previous[-1]


def normalize_zh(text: str) -> str:
    simplified = _T2S.convert(text)
    return "".join(ch for ch in simplified if "\u4e00" <= ch <= "\u9fff")


def normalize_en(text: str) -> list[str]:
    return _EN_TOKEN_RE.findall(text.lower().replace("’", "'"))


def english_terms(text: str) -> list[str]:
    return [term for term in _EN_RE.findall(text) if len(term) >= 2]


def run_set(engine, post: Postprocessor, directory: Path, sample_rate: int) -> dict:
    rows = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    details = []
    ref_total = error_total = 0
    term_total = term_hits = 0
    for row in rows:
        samples, sr = load_wav(directory / row["audio"], sample_rate)
        text = post.process(engine.transcribe(float_to_int16(samples), sr).text)
        ref = row["transcript"]
        details.append({"id": row["id"], "reference": ref, "text": text})
        if directory.name == "yue":
            ref_norm = normalize_zh(ref)
            hyp_norm = normalize_zh(text)
            error_total += levenshtein(list(ref_norm), list(hyp_norm))
            ref_total += len(ref_norm)
        elif directory.name == "en":
            ref_norm = normalize_en(ref)
            hyp_norm = normalize_en(text)
            error_total += levenshtein(ref_norm, hyp_norm)
            ref_total += len(ref_norm)
        elif directory.name == "yue_en":
            for term in english_terms(ref):
                term_total += 1
                if term.lower() in text.lower():
                    term_hits += 1
    result = {"set": directory.name, "clips": len(rows), "details": details}
    if directory.name == "yue":
        result["metric"] = "CER"
        result["rate"] = error_total / ref_total if ref_total else 0.0
    elif directory.name == "en":
        result["metric"] = "WER"
        result["rate"] = error_total / ref_total if ref_total else 0.0
    else:
        result["metric"] = "English term recall"
        result["rate"] = term_hits / term_total if term_total else 0.0
        result["hits"] = term_hits
        result["terms"] = term_total
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="eval_suite")
    parser.add_argument("--config", default="configs/app.yaml")
    parser.add_argument("--eval-root", default=str(ROOT / "eval"))
    parser.add_argument("--output", default="")
    args = parser.parse_args(argv)

    cfg = AppConfig.load(args.config)
    engine = build_asr(cfg.asr)
    post = Postprocessor(cfg.postprocess)
    root = Path(args.eval_root)

    results = []
    for name in ("yue", "en", "yue_en"):
        result = run_set(engine, post, root / name, cfg.audio.sample_rate)
        results.append(result)
        if result["metric"] == "English term recall":
            print(
                f"{name}: English recall {result['hits']}/{result['terms']} "
                f"= {result['rate']:.1%} ({result['clips']} clips)"
            )
        else:
            print(f"{name}: {result['metric']} {result['rate']:.1%} ({result['clips']} clips)")

    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
