from __future__ import annotations

import re

from .config import PostprocessConfig

_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
_CN_NUM = "零〇一二三四五六七八九两"
_CN_UNIT = "十百千万亿"
_YEAR_RE = re.compile(rf"([{_CN_NUM}]{{4}})年")
_MONTH_RE = re.compile(rf"([{_CN_NUM}{_CN_UNIT}]{{1,2}})月")
_DAY_RE = re.compile(rf"([{_CN_NUM}{_CN_UNIT}]{{1,3}})[日号]")
_MONEY_RE = re.compile(rf"([{_CN_NUM}{_CN_UNIT}]+)[元块]")
_PERCENT_RE = re.compile(rf"百分之([{_CN_NUM}{_CN_UNIT}点]+)")

_EN_PUNCT = str.maketrans({"。": ".", "，": ",", "？": "?", "！": "!", "；": ";", "：": ":"})


def normalize_script_punctuation(text: str) -> str:
    """Use ASCII punctuation for pure-English text; keep Chinese punctuation otherwise."""
    if _CJK_RE.search(text):
        return text
    return text.translate(_EN_PUNCT)


class Postprocessor:
    """Punctuation, ITN and script normalization for ASR text."""

    def __init__(self, cfg: PostprocessConfig):
        self.cfg = cfg
        self._punct = None
        self._converter = None
        self._cn2an = None
        self._load()

    def _load(self) -> None:
        if self.cfg.punctuation:
            if not self.cfg.punctuation_model:
                raise ValueError(
                    "postprocess.punctuation_model is required when punctuation is enabled"
                )
            import sherpa_onnx

            self._punct = sherpa_onnx.OfflinePunctuation(
                sherpa_onnx.OfflinePunctuationConfig(
                    model=sherpa_onnx.OfflinePunctuationModelConfig(
                        ct_transformer=self.cfg.punctuation_model,
                        num_threads=2,
                    )
                )
            )

        if self.cfg.output_script in {"simplified", "traditional"}:
            from opencc import OpenCC

            self._converter = OpenCC(
                "t2s" if self.cfg.output_script == "simplified" else "s2t"
            )

        if self.cfg.itn:
            try:
                import cn2an

                self._cn2an = cn2an
            except ImportError:
                self._cn2an = None

    def process(self, text: str) -> str:
        text = text.strip()
        if not text:
            return text

        if self._converter is not None:
            text = self._converter.convert(text)

        if self._cn2an is not None:
            text = self._apply_itn(text)

        if self._punct is not None:
            text = self._punct.add_punctuation(text)

        return normalize_script_punctuation(text).strip()

    def _apply_itn(self, text: str) -> str:
        """Conservative ITN: only convert numerals attached to clear units."""
        cn2an = self._cn2an
        if cn2an is None:
            return text

        def convert(match: re.Match, suffix: str) -> str:
            try:
                number = cn2an.cn2an(match.group(1), "smart")
            except Exception:
                return match.group(0)
            return f"{number}{suffix}"

        text = _YEAR_RE.sub(lambda m: convert(m, "年"), text)
        text = _MONTH_RE.sub(lambda m: convert(m, "月"), text)
        text = _DAY_RE.sub(lambda m: convert(m, "日"), text)
        text = _MONEY_RE.sub(lambda m: convert(m, "元"), text)
        text = _PERCENT_RE.sub(lambda m: convert(m, "%"), text)
        return text
