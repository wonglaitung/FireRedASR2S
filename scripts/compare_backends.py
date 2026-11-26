from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from firered_poc.asr import build_asr
from firered_poc.audio import float_to_int16, load_wav
from firered_poc.config import AppConfig
from firered_poc.postprocess import Postprocessor


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="compare_backends")
    parser.add_argument("--ctc-config", default="configs/app_ctc.yaml")
    parser.add_argument("--aed-config", default="configs/app.yaml")
    parser.add_argument("--wavs", nargs="+", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    ctc_cfg = AppConfig.load(args.ctc_config)
    aed_cfg = AppConfig.load(args.aed_config)
    ctc = build_asr(ctc_cfg.asr)
    aed = build_asr(aed_cfg.asr)
    ctc_post = Postprocessor(ctc_cfg.postprocess)
    aed_post = Postprocessor(aed_cfg.postprocess)
    sample_rate = ctc_cfg.audio.sample_rate

    rows = []
    for wav in args.wavs:
        samples, sr = load_wav(wav, sample_rate)
        pcm = float_to_int16(samples)

        t0 = time.perf_counter()
        ctc_text = ctc_post.process(ctc.transcribe(pcm, sr).text)
        ctc_dt = time.perf_counter() - t0

        t0 = time.perf_counter()
        aed_text = aed_post.process(aed.transcribe(pcm, sr).text)
        aed_dt = time.perf_counter() - t0

        rows.append(
            {
                "audio": Path(wav).name,
                "duration_s": round(samples.size / sr, 2),
                "ctc_seconds": round(ctc_dt, 2),
                "aed_seconds": round(aed_dt, 2),
                "ctc_text": ctc_text,
                "aed_text": aed_text,
            }
        )
        print(f"{Path(wav).name} ({rows[-1]['duration_s']}s)")
        print(f"  CTC {ctc_dt:.2f}s: {ctc_text}")
        print(f"  AED {aed_dt:.2f}s: {aed_text}")

    print(json.dumps(rows, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
