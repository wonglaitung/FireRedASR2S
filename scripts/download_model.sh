#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODELS="$ROOT/models"
NAME="sherpa-onnx-fire-red-asr2-ctc-zh_en-int8-2026-02-25"
URL="https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/${NAME}.tar.bz2"

mkdir -p "$MODELS"

if [ -d "$MODELS/$NAME" ]; then
  echo "model already present: $MODELS/$NAME"
  exit 0
fi

curl -L --retry 3 -o "$MODELS/${NAME}.tar.bz2" "$URL"
tar -xjf "$MODELS/${NAME}.tar.bz2" -C "$MODELS"
rm -f "$MODELS/${NAME}.tar.bz2"
echo "model ready: $MODELS/$NAME"
