#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODELS="$ROOT/models"

for item in \
  "sherpa-onnx-fire-red-asr2-zh_en-int8-2026-02-26" \
  "sherpa-onnx-punct-ct-transformer-zh-en-vocab272727-2024-04-12-int8" \
  "silero_vad.onnx"; do
  if [ ! -e "$MODELS/$item" ]; then
    echo "missing model: $MODELS/$item" >&2
    echo "run ./scripts/download_model.sh --aed-only first" >&2
    exit 1
  fi
done

cd "$ROOT"

docker build --build-arg SKIP_MODELS=1 -t firered-asr:base .
docker build --build-context models="$MODELS" -f Dockerfile.local -t firered-asr:latest .

echo "image ready: firered-asr:latest"
