#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODELS="$ROOT/models"
BASE_IMAGE="${BASE_IMAGE:-pytorch/pytorch:2.10.0-cuda12.8-cudnn9-runtime}"

for item in \
  "FireRedASR2-AED/model.pth.tar" \
  "FireRedASR2-AED/dict.txt" \
  "FireRedASR2S-code/fireredasr2s/fireredasr2/asr.py" \
  "silero_vad.onnx" \
  "sherpa-onnx-punct-ct-transformer-zh-en-vocab272727-2024-04-12-int8/model.int8.onnx"; do
  if [ ! -e "$MODELS/$item" ]; then
    echo "missing model/code: $MODELS/$item" >&2
    echo "run setup_official_aed.sh and download the punctuation/Silero models first" >&2
    exit 1
  fi
done

cd "$ROOT"
DOCKER_BUILDKIT=1 docker build \
  --build-arg BASE_IMAGE="$BASE_IMAGE" \
  --build-context models="$MODELS" \
  -f Dockerfile.gpu \
  -t firered-asr:gpu .

echo "image ready: firered-asr:gpu"
echo "run: docker run --gpus all -p 8000:8000 --restart unless-stopped firered-asr:gpu"
