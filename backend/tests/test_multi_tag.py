from pathlib import Path
import sys

import pytest

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
sys.path.insert(0, str(BACKEND))

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

    questions = parse_questions_from_text(text, parse_group_tags=True)

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

    questions = parse_questions_from_text(text, parse_group_tags=True)

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

    questions = parse_questions_from_text(text, ["shared", "ui-tag"], parse_group_tags=True)

    assert questions[0]["tags"] == ["de0", "alpha", "beta", "shared", "ui-tag"]


def test_group_tag_parser_accepts_special_ascii_characters():
    text = """@tag: alpha.beta, c++, topic/name & review
Question with special tags?
(x) Correct
( ) Wrong"""

    questions = parse_questions_from_text(text, parse_group_tags=True)

    assert questions[0]["tags"] == ["alpha.beta", "c++", "topic/name & review"]


def test_group_tag_parser_accepts_vietnamese_diacritics():
    text = """@tag: Ôn tập, Bài kiểm tra
Câu hỏi có tag tiếng Việt?
(x) Đúng
( ) Sai"""

    questions = parse_questions_from_text(text, parse_group_tags=True)

    assert questions[0]["tags"] == ["Ôn tập", "Bài kiểm tra"]


def test_group_marker_at_start_of_input():
    text = """@tag: first-group
Question?
(x) Correct
( ) Wrong"""

    questions = parse_questions_from_text(text, parse_group_tags=True)

    assert questions[0]["tags"] == ["first-group"]


def test_consecutive_group_markers_use_the_last_marker():
    text = """@tag: ignored
@tag: active
Question?
(x) Correct
( ) Wrong"""

    questions = parse_questions_from_text(text, parse_group_tags=True)

    assert questions[0]["tags"] == ["active"]


def test_empty_group_marker_at_start_produces_no_group_tags():
    text = """@tag:
Question?
(x) Correct
( ) Wrong"""

    questions = parse_questions_from_text(text, parse_group_tags=True)

    assert questions[0]["tags"] == []


def test_group_marker_is_ignored_by_default_for_llm_fallback_parser():
    text = """@tag: alpha
Question?
(x) Correct
( ) Wrong"""

    questions = parse_questions_from_text(text)

    assert len(questions) == 1
    assert questions[0]["tags"] == []


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

    questions = parse_multiple_select_questions_from_text(text, ["shared"], parse_group_tags=True)

    assert [q["tags"] for q in questions] == [
        ["alpha", "beta", "shared"],
        ["alpha", "beta", "shared"],
        ["gamma", "shared"],
    ]


def test_existing_sample_retains_legacy_group_tags(basic_questions):
    assert len(basic_questions) == 3
    assert [q["tags"] for q in basic_questions] == [
        ["de0"],
        ["de0"],
        ["de1"],
    ]
