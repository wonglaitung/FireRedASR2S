# AGENTS.md

## What this repo is
- **Design-stage only**: currently `docs/ARCHITECTURE.md`, `AGENTS.md`, `progress.md`. No source code, build, test, lint, or CI yet. Do not invent commands or claim checks pass.
- Goal: **accuracy-first, sentence-level (non-streaming) trilingual ASR** — Cantonese + Mandarin + English, including intra-sentence code-switching — built around FireRedASR2S.
- Remote: `git@github.com:wonglaitung/FireRedASR2S.git` (branch `main`). It is **not** upstream `github.com/FireRedTeam/FireRedASR2S`; upstream is reference only, not vendored here.

## Read first
- `docs/ARCHITECTURE.md` — source of truth, locked decisions, current version. Update it before any code/spec change that alters the architecture.
- `progress.md` — current status, done, todo, risks.

## Locked decisions (do not drift)
- **Initial default ASR = FireRedASR2-AED (1B+, BF16, balanced/high-concurrency).** LLM is the accuracy upgrade / low-confidence second pass; FunASR SenseVoice is last-resort degradation.
- **Accuracy first (phased)**: initial ships AED for throughput; never use INT8, shorten segments, or tighten endpointing just to cut latency; LLM remains the accuracy upgrade path.
- One unified multilingual model; **no hard language routing**. FireRedLID is optional metadata/hint only.
- **Sentence-level**: streaming VAD + non-streaming full-sentence inference. No word-by-word streaming ASR.
- Segmentation: pre-roll 300ms, post-roll 300ms; accuracy silence 550ms / overlap 600ms, balanced (initial) silence 450ms / overlap 400ms.
- Server stack: Python; WebSocket; 16kHz/16bit/mono PCM.

## Progress updates (required)
- Update `progress.md` **immediately** when a task completes, a decision is made, a risk is found, the plan changes, or a session ends. Do not wait for milestones.
- Must include at least: current status, completed items, todo, risks/blockers.
- If a change affects the design, update `docs/ARCHITECTURE.md` first, then sync `progress.md`.

## Validation requirements
- **Actually run checks** before claiming completion; never state a result you did not execute.
- After code changes: run `ruff check .`, then `python3 -m pytest`. Order: lint → typecheck (when configured) → test.
- A pytest baseline of **44 passed, 8 skipped** was reported, but `main` currently contains **no tests**; confirm the suite exists before trusting or quoting that number.
- After doc edits: verify every **Mermaid** block and Markdown code fence is paired and closed.
- Every gate conclusion (lint / test / docs) must cite a concrete report artifact (e.g. `/tmp/opencode/reports/` or CI artifacts); **do not commit report files to the repo**.

## Documentation rules
- Write in **Chinese Markdown**.
- Prefer **Mermaid** for architecture and flow diagrams.
- Explain a term in parentheses at its **first occurrence**.
- **Bump the doc version** on every change; do not maintain a revision log.
- Sync `progress.md` at each milestone and per the progress rules above.
- **Do not modify sections unrelated to the task.**

## Environment notes (verify; may change)
- Host has an RTX 4090 (24GB), but installed `torch`/`torchaudio` are **CPU-only** (`2.10.0+cpu`). GPU inference needs a CUDA-enabled build.
- `modelscope` is installed; **FunASR is not**. FireRedASR2S weights are **not downloaded**.
- `pytest 9.0.2` and `ruff 0.15.14` are available globally. No project config yet.
- No `README`, `pyproject.toml`, CI, or test config exists.

## Conventions
- Design docs are in **Chinese**; keep terminology consistent with `docs/ARCHITECTURE.md`.
- Commit history uses conventional prefixes (`docs: ...`). Only commit/push when explicitly asked.
