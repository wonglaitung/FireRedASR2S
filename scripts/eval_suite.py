#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from opencc import OpenCC

from firered_poc.asr import build_asr
from firered_poc.audio import float_to_int16, load_wav
from firered_poc.config import AppConfig
from firered_poc.postprocess import Postprocessor

ROOT = Path(__file__).resolve().parents[1]
_T2S = OpenCC("t2s")
_EN_TOKEN_RE = re.compile(r"[a-z0-9]+(?:['\-][a-z0-9]+)*")
_MIXED_TOKEN_RE = re.compile(r"[\u4e00-\u9fff]|[A-Za-z0-9]+(?:['\-][A-Za-z0-9]+)*")


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
    """Lower-case English word tokens with token-boundary matching."""
    return _EN_TOKEN_RE.findall(text.lower().replace("’", "'"))


def english_tokens(text: str) -> list[str]:
    """English terms used by the code-switch metric (ignore single letters/numbers)."""
    return [
        token
        for token in normalize_en(text)
        if len(token) >= 2 and any(ch.isalpha() for ch in token)
    ]


def mixed_tokens(text: str) -> list[str]:
    """Chinese characters and English words, both as single metric units."""
    simplified = _T2S.convert(text)
    tokens: list[str] = []
    for match in _MIXED_TOKEN_RE.finditer(simplified):
        token = match.group(0)
        tokens.append(token if "\u4e00" <= token <= "\u9fff" else token.lower())
    return tokens


def english_scores(reference: str, hypothesis: str) -> dict:
    ref_counts = Counter(english_tokens(reference))
    hyp_counts = Counter(english_tokens(hypothesis))
    hits = sum((ref_counts & hyp_counts).values())
    ref_total = sum(ref_counts.values())
    hyp_total = sum(hyp_counts.values())
    precision = hits / hyp_total if hyp_total else 0.0
    recall = hits / ref_total if ref_total else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "hits": hits,
        "ref_terms": ref_total,
        "hyp_terms": hyp_total,
    }


def run_set(engine, post: Postprocessor, directory: Path, sample_rate: int) -> dict:
    rows = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    details = []
    ref_total = error_total = 0
    term_total = term_hits = hyp_terms = 0
    for row in rows:
        samples, sr = load_wav(directory / row["audio"], sample_rate)
        raw_text = engine.transcribe(float_to_int16(samples), sr).text
        text = post.process(raw_text)
        ref = row["transcript"]
        detail = {
            "id": row["id"],
            "reference": ref,
            "raw_text": raw_text,
            "text": text,
        }
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
            ref_tokens = mixed_tokens(ref)
            hyp_tokens = mixed_tokens(text)
            scores = english_scores(ref, text)
            error_total += levenshtein(ref_tokens, hyp_tokens)
            ref_total += len(ref_tokens)
            term_total += scores["ref_terms"]
            term_hits += scores["hits"]
            hyp_terms += scores["hyp_terms"]
            detail["english"] = {
                "reference": english_tokens(ref),
                "hypothesis": english_tokens(text),
                "hits": scores["hits"],
            }
        details.append(detail)

    result = {"set": directory.name, "clips": len(rows), "details": details}
    if directory.name == "yue":
        result["metric"] = "CER"
        result["rate"] = error_total / ref_total if ref_total else 0.0
        result["errors"] = error_total
        result["units"] = ref_total
    elif directory.name == "en":
        result["metric"] = "WER"
        result["rate"] = error_total / ref_total if ref_total else 0.0
        result["errors"] = error_total
        result["units"] = ref_total
    else:
        result["metric"] = "English term F1"
        precision = term_hits / hyp_terms if hyp_terms else 0.0
        recall = term_hits / term_total if term_total else 0.0
        result["metrics"] = {
            "english_precision": precision,
            "english_recall": recall,
            "english_f1": (
                2 * precision * recall / (precision + recall)
                if precision + recall
                else 0.0
            ),
            "mixed_cer": error_total / ref_total if ref_total else 0.0,
        }
        result["hits"] = term_hits
        result["terms"] = term_total
        result["hyp_terms"] = hyp_terms
        result["rate"] = result["metrics"]["english_recall"]
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
        if name == "yue_en":
            metrics = result["metrics"]
            print(
                f"yue_en: English F1 {metrics['english_f1']:.1%} "
                f"(P {metrics['english_precision']:.1%} / "
                f"R {metrics['english_recall']:.1%}), "
                f"mixed CER {metrics['mixed_cer']:.1%} ({result['clips']} clips)"
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
