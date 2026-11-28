#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CACHE="${FIREREDASR2S_CACHE:-$ROOT/models}"
CODE_DIR="$CACHE/FireRedASR2S-code"
MODEL_DIR="$CACHE/FireRedASR2-AED"
MODEL_BASE="https://huggingface.co/FireRedTeam/FireRedASR2-AED/resolve/main"

mkdir -p "$CACHE" "$MODEL_DIR"

if [ ! -f "$CODE_DIR/fireredasr2s/fireredasr2/asr.py" ]; then
  git clone --depth 1 https://github.com/FireRedTeam/FireRedASR2S.git "$CODE_DIR"
fi

download() {
  local name="$1"
  local expected="$2"
  local out="$MODEL_DIR/$name"
  if [ -f "$out" ]; then
    local size
    size="$(stat -c%s "$out")"
    if [ "$size" = "$expected" ]; then
      echo "skip $name (cached)"
      return
    fi
    if [ "$size" -gt "$expected" ]; then
      rm -f "$out"
    fi
  fi
  echo "download $name"
  curl -L --fail --retry 20 --retry-delay 5 --retry-all-errors \
    --continue-at - -o "$out" "$MODEL_BASE/$name"
}

download cmvn.ark 1311
download dict.txt 79172
download train_bpe1000.model 251707
download model.pth.tar 4731558506

echo "model cache: $MODEL_DIR"
echo "code cache:  $CODE_DIR"
