from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location("eval_suite", ROOT / "scripts" / "eval_suite.py")
assert _SPEC and _SPEC.loader
_MODULE = importlib.util.module_from_spec(_SPEC)
assert isinstance(_MODULE, ModuleType)
_SPEC.loader.exec_module(_MODULE)

english_scores = _MODULE.english_scores
english_tokens = _MODULE.english_tokens
mixed_tokens = _MODULE.mixed_tokens
normalize_en = _MODULE.normalize_en


def test_english_matching_is_token_bounded() -> None:
    scores = english_scores("IT is with you", "with it")
    assert scores["hits"] == 2
    assert scores["precision"] == 1.0
    assert scores["recall"] == 0.5


def test_english_normalization_strips_punctuation_and_apostrophes() -> None:
    assert normalize_en("You'") == ["you"]
    assert normalize_en("sushi, sashimi!") == ["sushi", "sashimi"]
    assert normalize_en("countdown") == ["countdown"]


def test_misspelled_english_term_is_not_a_hit() -> None:
    scores = english_scores("clothes", "CLOSER")
    assert scores["hits"] == 0
    assert scores["precision"] == 0.0
    assert scores["recall"] == 0.0


def test_english_terms_exclude_pure_numbers() -> None:
    assert english_tokens("10") == []
    assert english_tokens("5G") == ["5g"]


def test_mixed_tokens_keep_english_words_whole() -> None:
    tokens = mixed_tokens("粵語 mix temperature 10度")
    assert tokens[:2] == ["粤", "语"]
    assert "mix" in tokens
    assert "temperature" in tokens
    assert "10" in tokens
