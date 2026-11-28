# AGENTS.md

## What this repo is
- **Design-stage only**: currently `docs/ARCHITECTURE.md`, `AGENTS.md`, `progress.md`. No source code, build, test, lint, or CI yet. Do not invent commands or claim checks pass.
- Goal: **accuracy-first, sentence-level (non-streaming) trilingual ASR** — Cantonese + Mandarin + English, including intra-sentence code-switching — built around FireRedASR2S.
- Remote: `git@github.com:wonglaitung/FireRedASR2S.git` (branch `main`). It is **not** upstream `github.com/FireRedTeam/FireRedASR2S`; upstream is reference only, not vendored here.

## Read first
- `README.md` — quick start, architecture summary, recorder usage.
- `docs/ARCHITECTURE.md` — source of truth, locked decisions, current version. Update it before any code/spec change that alters the architecture.
- `docs/EVOLUTION.md` — learning-oriented evolution from the first POC to the current stage.
- `progress.md` — current status, done, todo, risks.

## Locked decisions (do not drift)
- **Initial default ASR = FireRedASR2-AED (1B+, BF16, balanced/high-concurrency).** LLM is the accuracy upgrade / low-confidence second pass. **Single engine only**: no FunASR or cross-engine fallback — retry once, then return an explicit error.
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
- The `main` suite currently reports **54 passed** (`ruff check .` clean).
- After doc edits: verify every **Mermaid** block and Markdown code fence is paired and closed.
- Every gate conclusion (lint / test / docs) must cite a concrete report artifact (a temporary report directory or CI artifacts); **do not commit report files to the repo**.

## Documentation rules
- Write in **Chinese Markdown**.
- Prefer **Mermaid** for architecture and flow diagrams.
- Explain a term in parentheses at its **first occurrence**.
- **Bump the doc version** on every change; do not maintain a revision log.
- Sync `progress.md` at each milestone and per the progress rules above.
- **Do not modify sections unrelated to the task.**

## Environment notes (verify; may change)
- Host has an RTX 4090 (24GB); the default environment has CPU-only `torch` (`2.10.0+cpu`). The official AED adapter needs a CUDA torch environment; its model/code cache is under `models/` (`setup_official_aed.sh`).
- `modelscope` is installed; **FunASR is not, and is out of scope** (single-engine policy). POC models live in `models/` (gitignored): FireRedASR2 AED ONNX, Silero VAD, CT-Transformer punctuation.
- `pytest 9.0.2`, `ruff 0.15.14`, `sherpa-onnx`, `cn2an`, and `OpenCC` are available. `PyQt6` is available for the desktop recorder. `pyproject.toml` and `configs/` exist; GitHub Actions builds the recorder.

## Desktop recorder
- `PYTHONPATH=src python3 -m firered_recorder` opens the PyQt6 recorder (backend must already be running).
- Headless verification: `--file <wav> --no-realtime`.
- Build: `python scripts/build_recorder.py` (PyInstaller). Windows exe must be built on Windows or via `.github/workflows/build-recorder.yml`; PyInstaller cannot cross-compile.
- Standalone desktop recorder; see `docs/RECORDER.md`.

## Eval data
- `docs/DATA.md` defines the internal dictation/meeting collection, annotation, split, and validation protocol.
- `eval/yue/` (20 pure Cantonese, words.hk CC BY 4.0), `eval/en/` (20 English, LibriSpeech CC BY 4.0), `eval/yue_en/` (20 Cantonese-English, MCE research-only).
- Baseline (100 code-switch clips): sherpa int8 84.3% F1 / 7.2% mixed CER; official AED beam10 87.4% / 6.5%; official AED + n-best LM 88.4% / 6.0%. Cantonese CER 4.7%, English WER 0.9%. On the original 20-clip easier subset, LM reaches 95.4% F1. On 153 spontaneous WSYue clips, 1-best is 71.5% F1 / 10.1% mixed CER and the MCE LM degrades to 70.5% / 10.2%. On 100 SwitchLingua dictation-proxy clips, 1-best is 88.5% / 6.6% and the MCE LM degrades to 83.2% / 9.4%.
- Run all: `PYTHONPATH=src python3 scripts/eval_suite.py --config configs/app.yaml --output eval/baseline_aed.json`.
- MCE is not commercial-clear and is not an official benchmark.

## Backend Docker
- `docker build -t firered-asr:latest .` + `docker run`; see `docs/DOCKER.md`. Single container: no compose.
- Default bakes AED + Silero + punctuation.
- `SKIP_MODELS=1` builds a small image for mounting `models/` at `/app/models`.
- CPU sherpa image: `bash scripts/build_docker_local.sh` (`Dockerfile.local` + build context).
- GPU official AED image: `bash scripts/build_docker_gpu_local.sh` (`Dockerfile.gpu` + local model/code cache; run with `--gpus all`).

## Conventions
- Design docs are in **Chinese**; keep terminology consistent with `docs/ARCHITECTURE.md`.
- Commit history uses conventional prefixes (`docs: ...`). Only commit/push when explicitly asked.
