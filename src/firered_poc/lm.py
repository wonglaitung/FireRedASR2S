from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path

from opencc import OpenCC

_T2S = OpenCC("t2s")
_TOKEN_RE = re.compile(r"[\u4e00-\u9fff]|[A-Za-z0-9]+(?:['\-][A-Za-z0-9]+)*")
_SEP = "\x1f"


def mixed_tokenize(text: str) -> list[str]:
    """Chinese chars and English words as LM units."""
    simplified = _T2S.convert(text)
    return [
        token if "\u4e00" <= token <= "\u9fff" else token.lower()
        for token in _TOKEN_RE.findall(simplified)
    ]


class MixedNgramLM:
    """Small interpolated trigram LM for code-switch n-best rescoring."""

    def __init__(self, uni: Counter, bi: Counter, tri: Counter):
        self.uni = uni
        self.bi = bi
        self.tri = tri
        self.vocab_size = len(uni)
        self.total = sum(uni.values())

    @classmethod
    def train(cls, sentences: list[str]) -> MixedNgramLM:
        uni: Counter = Counter()
        bi: Counter = Counter()
        tri: Counter = Counter()
        for sentence in sentences:
            tokens = ["<s>", "<s>", *mixed_tokenize(sentence), "</s>"]
            for i, token in enumerate(tokens):
                uni[token] += 1
                if i >= 1:
                    bi[_SEP.join(tokens[i - 1 : i + 1])] += 1
                if i >= 2:
                    tri[_SEP.join(tokens[i - 2 : i + 1])] += 1
        return cls(uni, bi, tri)

    @classmethod
    def load(cls, path: str | Path) -> MixedNgramLM:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(Counter(raw["uni"]), Counter(raw["bi"]), Counter(raw["tri"]))

    def save(self, path: str | Path) -> None:
        payload = {"uni": dict(self.uni), "bi": dict(self.bi), "tri": dict(self.tri)}
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def score(self, text: str) -> float:
        tokens = mixed_tokenize(text)
        padded = ["<s>", "<s>", *tokens, "</s>"]
        total = 0.0
        for i in range(2, len(padded)):
            prev2, prev1, token = padded[i - 2], padded[i - 1], padded[i]
            c3 = self.tri.get(_SEP.join((prev2, prev1, token)), 0)
            c2 = self.bi.get(_SEP.join((prev2, prev1)), 0)
            c1 = self.uni.get(prev1, 0)
            if c3 and c2:
                prob = c3 / c2
            elif c2 and c1:
                prob = 0.4 * c2 / c1
            else:
                prob = 0.4 * (self.uni.get(token, 0) + 0.1) / (
                    self.total + 0.1 * self.vocab_size
                )
            total += math.log(max(prob, 1e-9))
        return total / max(len(tokens), 1)
