from __future__ import annotations

from firered_poc.asr.official import FireRedTorchASR
from firered_poc.lm import MixedNgramLM, mixed_tokenize


def test_mixed_tokenize_keeps_english_words() -> None:
    assert mixed_tokenize("我like food court") == ["我", "like", "food", "court"]


def test_lm_prefers_seen_code_switch_phrase() -> None:
    lm = MixedNgramLM.train(["我钟意去food court食饭", "food court好wide"])
    assert lm.score("food court") > lm.score("footcock")


def test_lm_roundtrip(tmp_path) -> None:
    lm = MixedNgramLM.train(["今日好hot", "带sunscreen"])
    path = tmp_path / "lm.json"
    lm.save(path)
    loaded = MixedNgramLM.load(path)
    assert loaded.score("带sunscreen") == lm.score("带sunscreen")


def test_code_switch_detection() -> None:
    assert FireRedTorchASR._is_code_switch("我like it")
    assert not FireRedTorchASR._is_code_switch("我钟意")
    assert not FireRedTorchASR._is_code_switch("hello world")
