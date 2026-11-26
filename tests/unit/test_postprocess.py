from __future__ import annotations

from pathlib import Path

import pytest

from firered_poc.config import PostprocessConfig
from firered_poc.postprocess import Postprocessor, normalize_script_punctuation

ROOT = Path(__file__).resolve().parents[2]
PUNCT_MODEL = (
    ROOT
    / "models"
    / "sherpa-onnx-punct-ct-transformer-zh-en-vocab272727-2024-04-12-int8"
    / "model.int8.onnx"
)


def test_itn_converts_chinese_numbers() -> None:
    post = Postprocessor(PostprocessConfig(itn=True, output_script="as-is"))
    assert post.process("二零二六年十一月") == "2026年11月"
    assert post.process("三千五百元") == "3500元"
    assert post.process("百分之五十") == "50%"
    assert post.process("礼拜八二") == "礼拜八二"


def test_english_punctuation_is_ascii() -> None:
    assert normalize_script_punctuation("HELLO。") == "HELLO."
    assert normalize_script_punctuation("你好。") == "你好。"


def test_opencc_simplifies_text() -> None:
    post = Postprocessor(
        PostprocessConfig(itn=False, output_script="simplified")
    )
    assert post.process("呢幾個字") == "呢几个字"


def test_opencc_traditionalizes_text() -> None:
    post = Postprocessor(
        PostprocessConfig(itn=False, output_script="traditional")
    )
    assert post.process("汉字") == "漢字"


def test_empty_text_is_unchanged() -> None:
    post = Postprocessor(PostprocessConfig())
    assert post.process("   ") == ""


@pytest.mark.skipif(not PUNCT_MODEL.exists(), reason="punctuation model not downloaded")
def test_punctuation_adds_marks() -> None:
    post = Postprocessor(
        PostprocessConfig(
            punctuation=True,
            punctuation_model=str(PUNCT_MODEL),
            itn=False,
            output_script="as-is",
        )
    )
    out = post.process("今天天气很好我们去公园吧")
    assert "，" in out or "。" in out
