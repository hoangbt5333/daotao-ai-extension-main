import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.api.v1.endpoints.questions import (
    parse_multiple_select_questions_from_text,
    parse_questions_from_text,
)


@pytest.fixture
def basic_questions():
    text = (ROOT / "samples" / "q_basic.txt").read_text(encoding="utf-8")
    return parse_questions_from_text(text)


def test_group_marker_applies_until_next_marker():
    text = """@tag: alpha, beta
Question one?
(x) Correct
( ) Wrong
Question two?
(x) Correct
( ) Wrong
@tag: gamma
Question three?
(x) Correct
( ) Wrong"""

    questions = parse_questions_from_text(text)

    assert [q["tags"] for q in questions] == [
        ["alpha", "beta"],
        ["alpha", "beta"],
        ["gamma"],
    ]


def test_empty_group_marker_clears_group_tags():
    text = """@tag: alpha
Question tagged?
(x) Correct
( ) Wrong
@tag:
Question untagged?
(x) Correct
( ) Wrong"""

    questions = parse_questions_from_text(text)

    assert [q["tags"] for q in questions] == [["alpha"], []]


def test_legacy_de_markers_and_ui_tags_remain_available():
    text = """de0
Question in first group?
(x) Correct
( ) Wrong
de1
Question in second group?
(x) Correct
( ) Wrong"""

    questions = parse_questions_from_text(text, ["shared", "shared"])

    assert [q["tags"] for q in questions] == [
        ["de0", "shared"],
        ["de1", "shared"],
    ]


def test_group_tags_merge_with_legacy_tags_without_duplicates():
    text = """de0
@tag: alpha, beta, alpha, de0, shared
Question with combined tags?
(x) Correct
( ) Wrong"""

    questions = parse_questions_from_text(text, ["shared", "ui-tag"])

    assert questions[0]["tags"] == ["de0", "alpha", "beta", "shared", "ui-tag"]


def test_group_tag_parser_accepts_special_ascii_characters():
    text = """@tag: alpha.beta, c++
Question with special tags?
(x) Correct
( ) Wrong"""

    questions = parse_questions_from_text(text)

    assert questions[0]["tags"] == ["alpha.beta", "c++"]


def test_group_tags_work_with_multiple_select_custom_parser():
    text = """@tag: alpha, beta
Question one?
[x] Correct
[ ] Wrong
Question two?
[ ] Wrong
[x] Correct
@tag: gamma
Question three?
[x] Correct
[ ] Wrong"""

    questions = parse_multiple_select_questions_from_text(text, ["shared"])

    assert [q["tags"] for q in questions] == [
        ["alpha", "beta", "shared"],
        ["alpha", "beta", "shared"],
        ["gamma", "shared"],
    ]


def test_five_question_sample_retains_legacy_group_tags(basic_questions):
    assert len(basic_questions) == 5
    assert [q["tags"] for q in basic_questions] == [
        ["de0"],
        ["de0"],
        ["de0"],
        ["de1"],
        ["de1"],
    ]
