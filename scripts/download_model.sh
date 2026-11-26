#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODELS="$ROOT/models"
BASE="https://github.com/k2-fsa/sherpa-onnx/releases/download"

CTC="sherpa-onnx-fire-red-asr2-ctc-zh_en-int8-2026-02-25"
PUNCT="sherpa-onnx-punct-ct-transformer-zh-en-vocab272727-2024-04-12-int8"
AED="sherpa-onnx-fire-red-asr2-zh_en-int8-2026-02-26"

mkdir -p "$MODELS"

fetch_and_extract() {
  local name="$1"
  local url="$2"
  if [ -d "$MODELS/$name" ]; then
    echo "model already present: $MODELS/$name"
    return 0
  fi
  curl -L --retry 3 -o "$MODELS/$name.tar.bz2" "$url"
  tar -xjf "$MODELS/$name.tar.bz2" -C "$MODELS"
  rm -f "$MODELS/$name.tar.bz2"
  echo "model ready: $MODELS/$name"
}

fetch_and_extract "$CTC" "$BASE/asr-models/$CTC.tar.bz2"
fetch_and_extract "$AED" "$BASE/asr-models/$AED.tar.bz2"
fetch_and_extract "$PUNCT" "$BASE/punctuation-models/$PUNCT.tar.bz2"

if [ ! -f "$MODELS/silero_vad.onnx" ]; then
  curl -L --retry 3 -o "$MODELS/silero_vad.onnx" "$BASE/asr-models/silero_vad.onnx"
  echo "model ready: $MODELS/silero_vad.onnx"
else
  echo "model already present: $MODELS/silero_vad.onnx"
fi
