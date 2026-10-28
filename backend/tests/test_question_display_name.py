"""
Tests for question display_name resolution in LibraryExporter and OpenEdXExporter.
Verifies:
- resolve_question_display_name helper: naming, sequence fallback, duplicate suffixing, special chars, Vietnamese
- Library export: problem XML display_name with special characters, Vietnamese, duplicates, empty fallback
- Support for radio (multiple_choice), multiple_select, text_input, numerical
- OpenEdX course export problem display_name
- Preservation of tags (@tag: and legacy de0/de1)
"""
import os
import sys
from pathlib import Path
import tempfile
import tarfile
import pytest
from lxml import etree

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.services.export.helpers import resolve_question_display_name
from app.services.export.library import LibraryExporter
from app.services.export.openedx import OpenEdXExporter


# ============================================================================
# Unit tests: resolve_question_display_name
# ============================================================================

def test_resolve_explicit_name():
    used = {}
    q = {"name": "CauHoi-01", "question": "Noi dung cau hoi"}
    name = resolve_question_display_name(q, 0, used)
    assert name == "CauHoi-01"


def test_resolve_fallback_when_name_missing_or_empty():
    used = {}
    q_none = {"question": "No name"}
    q_empty = {"name": "", "question": "Empty name"}
    q_ws = {"name": "   ", "question": "Whitespace name"}

    assert resolve_question_display_name(q_none, 0, used) == "Cau-01"
    assert resolve_question_display_name(q_empty, 1, used) == "Cau-02"
    assert resolve_question_display_name(q_ws, 2, used) == "Cau-03"


def test_resolve_fallback_two_digits_padding():
    used = {}
    for i in range(12):
        name = resolve_question_display_name({}, i, used)
        expected = f"Cau-{i + 1:02d}"
        assert name == expected


def test_resolve_vietnamese_diacritics():
    used = {}
    q = {"name": "Câu 1: Ôn tập & Kiểm tra kiến thức", "question": "Hỏi gì đó"}
    name = resolve_question_display_name(q, 0, used)
    assert name == "Câu 1: Ôn tập & Kiểm tra kiến thức"


def test_resolve_special_xml_characters():
    used = {}
    q = {"name": "Q: a < b & c > d và \"quote\"", "question": "Hỏi gì đó"}
    name = resolve_question_display_name(q, 0, used)
    assert name == "Q: a < b & c > d và \"quote\""


def test_resolve_duplicate_names_adds_suffix():
    used = {}
    q1 = {"name": "Quiz-A"}
    q2 = {"name": "Quiz-A"}
    q3 = {"name": "Quiz-A"}

    name1 = resolve_question_display_name(q1, 0, used)
    name2 = resolve_question_display_name(q2, 1, used)
    name3 = resolve_question_display_name(q3, 2, used)

    assert name1 == "Quiz-A"
    assert name2 == "Quiz-A_1"
    assert name3 == "Quiz-A_2"


def test_resolve_duplicate_fallback_names():
    used = {}
    # Both question 0 and an explicit question named Cau-01
    q0 = {}
    q1 = {"name": "Cau-01"}

    name0 = resolve_question_display_name(q0, 0, used)
    name1 = resolve_question_display_name(q1, 1, used)

    assert name0 == "Cau-01"
    assert name1 == "Cau-01_1"


def test_resolve_name_not_taken_from_choices():
    used = {}
    q = {
        "question": "Nội dung câu hỏi",
        "choices": ["Đáp án A có chữ Cau-99", "Đáp án B"]
    }
    name = resolve_question_display_name(q, 0, used)
    assert name == "Cau-01"
    assert "Cau-99" not in name


# ============================================================================
# Integration test: LibraryExporter
# ============================================================================

def test_library_exporter_problem_display_names():
    exporter = LibraryExporter()
    questions = [
        # 1. Radio (multiple_choice) with explicit name & Vietnamese & special chars
        {
            "name": "Câu 1: Hình học & Đại số (x < y & y > 0) \"chuẩn\"",
            "type": "multiple_choice",
            "question": "2 + 2 = ?",
            "choices": ["3", "4", "5"],
            "correct_answers": [1],
            "fixed_choices": [],
            "tags": ["toan", "de0"]
        },
        # 2. multiple_select with explicit name
        {
            "name": "Câu 2: Chọn nhiều đáp án",
            "type": "multiple_select",
            "question": "Số chẵn gồm?",
            "choices": ["2", "3", "4"],
            "correct_answers": [0, 2],
            "tags": ["toan", "de0"]
        },
        # 3. text_input with missing name (fallback to Cau-03)
        {
            "type": "text_input",
            "question": "Thủ đô của Việt Nam là gì?",
            "correct_answer": "Hà Nội",
            "tags": ["dia_ly"]
        },
        # 4. numerical with whitespace name (fallback to Cau-04)
        {
            "name": "   ",
            "type": "numerical",
            "question": "Số pi xấp xỉ?",
            "correct_answer": "3.14",
            "tags": ["toan"]
        },
        # 5. Duplicate name with Câu 2
        {
            "name": "Câu 2: Chọn nhiều đáp án",
            "type": "multiple_choice",
            "question": "Câu hỏi trùng tên",
            "choices": ["A", "B"],
            "correct_answers": [0],
            "fixed_choices": [],
            "tags": ["de1"]
        }
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        tar_path = os.path.join(tmpdir, "test_lib.tar.gz")
        export_data = {
            "questions": questions,
            "library_name": "Test Library Display Names",
            "org": "SoDiTEC",
            "library_code": "LIB_TEST",
            "start_time": '"2030-01-01T00:00:00Z"',
            "question_type": "multiple_choice"
        }

        success = exporter.export(export_data, tar_path)
        assert success is True
        assert os.path.exists(tar_path)

        # Extract and parse XML files
        extract_dir = os.path.join(tmpdir, "extracted")
        with tarfile.open(tar_path, "r:gz") as tar:
            tar.extractall(extract_dir)

        # Parse library.xml
        lib_xml_path = os.path.join(extract_dir, "library", "library.xml")
        assert os.path.exists(lib_xml_path)
        lib_tree = etree.parse(lib_xml_path)
        problem_refs = lib_tree.xpath("//problem")
        assert len(problem_refs) == 5

        # Check each problem XML
        problem_dir = os.path.join(extract_dir, "library", "problem")
        display_names = []
        for pref in problem_refs:
            url_name = pref.get("url_name")
            prob_file = os.path.join(problem_dir, f"{url_name}.xml")
            assert os.path.exists(prob_file)

            prob_tree = etree.parse(prob_file)
            root = prob_tree.getroot()
            assert root.tag == "problem"
            dname = root.get("display_name")
            display_names.append(dname)

        # Verify display_names match expected
        assert display_names[0] == "Câu 1: Hình học & Đại số (x < y & y > 0) \"chuẩn\""
        assert display_names[1] == "Câu 2: Chọn nhiều đáp án"
        assert display_names[2] == "Cau-03"
        assert display_names[3] == "Cau-04"
        assert display_names[4] == "Câu 2: Chọn nhiều đáp án_1"

        # Verify tags are preserved
        prob1_tree = etree.parse(os.path.join(problem_dir, f"{problem_refs[0].get('url_name')}.xml"))
        prob1_tags = prob1_tree.getroot().get("tags")
        assert "toan" in prob1_tags
        assert "de0" in prob1_tags


# ============================================================================
# Integration test: OpenEdXExporter
# ============================================================================

def test_openedx_exporter_problem_display_names():
    exporter = OpenEdXExporter()
    questions = [
        {
            "name": "Bài tập 1: Giải phương trình",
            "question": "x + 1 = 2",
            "choices": ["x = 1", "x = 2"],
            "correct_answers": [0]
        },
        {
            "name": "",  # Empty name -> Cau-02
            "question": "x + 2 = 4",
            "choices": ["x = 2", "x = 3"],
            "correct_answers": [0]
        }
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        tar_path = os.path.join(tmpdir, "course_test.tar.gz")
        course_data = {
            "name": "Khóa học test",
            "course": "TEST01",
            "org": "SoDiTEC",
            "chapters": [
                {
                    "title": "Chương 1",
                    "subsections": [
                        {
                            "title": "Bài 1",
                            "units": [
                                {
                                    "title": "Unit 1",
                                    "unit_type": "text",
                                    "html_content": "<p>Nội dung</p>"
                                }
                            ]
                        }
                    ]
                }
            ],
            "questions": questions
        }

        success = exporter.export(course_data, tar_path)
        assert success is True
        assert os.path.exists(tar_path)

        extract_dir = os.path.join(tmpdir, "extracted")
        with tarfile.open(tar_path, "r:gz") as tar:
            tar.extractall(extract_dir)

        prob_dir = os.path.join(extract_dir, "course", "problem")
        assert os.path.exists(prob_dir)
        prob_files = [f for f in os.listdir(prob_dir) if f.endswith(".xml")]
        assert len(prob_files) >= 1

        dnames = []
        for pf in prob_files:
            tree = etree.parse(os.path.join(prob_dir, pf))
            dnames.append(tree.getroot().get("display_name"))

        # There should be no "Multiple Choice" display_name
        assert "Multiple Choice" not in dnames
        # First problem chunk should have resolved name
        assert dnames[0] == "Bài tập 1: Giải phương trình"
