"""
TDD tests for multiple_select feature parity:
- Parser: 1, 2, all correct answers
- Validation: 0 correct rejected, < 2 choices rejected
- Marker variants: [!x], [@], [! ], [ ! ], [X], [], [ x ] - no data loss, no question split, warning added
- XML structure: real child elements, no &lt;, no shuffle/fixed on checkboxgroup/choice
- partial_credit: none (default), halves, EDC
- Special characters: &, <, >, "
- Display name and tags
- Full library export (.tar.gz)
"""
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

import json
import tarfile
import tempfile
import pytest
from lxml import etree

from app.api.v1.endpoints.questions import parse_multiple_select_questions_from_text
from app.services.export.helpers import build_single_problem_xml
from app.services.export.library import LibraryExporter


def test_parse_multiselect_one_correct():
    text = """de0
@tag: Tag1, Tag2
Câu 1: Câu hỏi một đáp án đúng trong multiple_select?
[x] Phương án A đúng
[ ] Phương án B sai
[ ] Phương án C sai
[ ] Phương án D sai
"""
    questions = parse_multiple_select_questions_from_text(text, parse_group_tags=True)
    assert len(questions) == 1
    q = questions[0]
    assert q["type"] == "multiple_select"
    assert q["is_valid"] is True
    assert len(q["choices"]) == 4
    assert q["correct_answers"] == [0]
    assert q["tags"] == ["de0", "Tag1", "Tag2"]
    assert q.get("errors", []) == []


def test_parse_multiselect_two_correct():
    text = """@tag: Python
Câu 2: Chọn hai đáp án đúng?
[x] Đáp án A
[ ] Đáp án B
[x] Đáp án C
[ ] Đáp án D
"""
    questions = parse_multiple_select_questions_from_text(text, parse_group_tags=True)
    assert len(questions) == 1
    q = questions[0]
    assert q["is_valid"] is True
    assert q["choices"] == ["Đáp án A", "Đáp án B", "Đáp án C", "Đáp án D"]
    assert q["correct_answers"] == [0, 2]
    assert q["tags"] == ["Python"]


def test_parse_multiselect_all_correct():
    text = """Câu 3: Chọn tất cả các đáp án đúng?
[x] Đúng 1
[x] Đúng 2
[x] Đúng 3
[x] Đúng 4
"""
    questions = parse_multiple_select_questions_from_text(text)
    assert len(questions) == 1
    q = questions[0]
    assert q["is_valid"] is True
    assert len(q["choices"]) == 4
    assert q["correct_answers"] == [0, 1, 2, 3]


def test_parse_multiselect_zero_correct_rejected():
    text = """Câu hỏi không có đáp án đúng nào?
[ ] Phương án 1
[ ] Phương án 2
[ ] Phương án 3
"""
    questions = parse_multiple_select_questions_from_text(text)
    assert len(questions) == 1
    q = questions[0]
    assert q["is_valid"] is False
    assert len(q["correct_answers"]) == 0
    assert any("ít nhất 1 đáp án đúng" in err for err in q["errors"])


def test_parse_multiselect_insufficient_choices_rejected():
    text = """Câu hỏi chỉ có 1 phương án?
[x] Phương án duy nhất
"""
    questions = parse_multiple_select_questions_from_text(text)
    assert len(questions) == 1
    q = questions[0]
    assert q["is_valid"] is False
    assert any("ít nhất 2 đáp án" in err for err in q["errors"])


def test_parse_multiselect_marker_variants_and_warning():
    """
    Test markers: [!x], [@], [! ], [ ! ], [X], [], [ x ]
    Must not drop choices or split questions.
    Flags ! and @ must be ignored (no shuffle/fixed), but warning is added.
    """
    text = """Câu hỏi kiểm tra biến thể marker:
[! ] Phương án A có ! và khoảng trắng
[X] Phương án B chữ X hoa
[@] Phương án C có @
[ ! x ] Phương án D có ! và x
[] Phương án E rỗng ngoặc
[ x ] Phương án F có cách
"""
    questions = parse_multiple_select_questions_from_text(text)
    assert len(questions) == 1
    q = questions[0]
    assert len(q["choices"]) == 6
    assert q["choices"][0] == "Phương án A có ! và khoảng trắng"
    assert q["choices"][1] == "Phương án B chữ X hoa"
    assert q["choices"][2] == "Phương án C có @"
    assert q["choices"][3] == "Phương án D có ! và x"
    assert q["choices"][4] == "Phương án E rỗng ngoặc"
    assert q["choices"][5] == "Phương án F có cách"

    # [X], [ ! x ], [ x ] are correct (indices 1, 3, 5)
    assert q["correct_answers"] == [1, 3, 5]
    assert q["is_valid"] is True

    # Warning must be present for ignored ! and @
    assert "warnings" in q
    assert any("không hỗ trợ xáo trộn" in w for w in q["warnings"])


def test_build_single_problem_xml_multiselect_structure_no_shuffle_no_fixed():
    question_data = {
        "name": "Cau-01",
        "question": "Câu hỏi kiểm tra cấu trúc XML?",
        "type": "multiple_select",
        "choices": ["Đáp án 1", "Đáp án 2", "Đáp án 3"],
        "correct_answers": [0, 2],
        "fixed_choices": [2],  # Phải bị bỏ qua với multiple_select
        "shuffle": True,        # Phải bị bỏ qua với multiple_select
        "tags": ["de0", "KiemThu"]
    }

    elem = build_single_problem_xml(question_data)
    assert elem.tag == "problem"
    assert elem.get("display_name") == "Cau-01"

    # Child elements must be real XML elements, not escaped strings
    cr = elem.find("choiceresponse")
    assert cr is not None
    assert "partial_credit" not in cr.attrib

    # Check preserved <p/> and <label>
    p_tags = cr.findall("p")
    assert len(p_tags) >= 2
    label = cr.find("label")
    assert label is not None
    assert label.text == "Chọn tất cả đáp án đúng"

    cbg = cr.find("checkboxgroup")
    assert cbg is not None
    # KHÔNG được có shuffle="true" trên checkboxgroup
    assert "shuffle" not in cbg.attrib

    choices = cbg.findall("choice")
    assert len(choices) == 3
    assert choices[0].get("correct") == "true"
    assert choices[1].get("correct") == "false"
    assert choices[2].get("correct") == "true"
    # KHÔNG được có fixed="true" trên choice của multiple_select
    for c in choices:
        assert "fixed" not in c.attrib


def test_build_single_problem_xml_partial_credit_options():
    q_data = {
        "name": "Cau-PC",
        "question": "Câu hỏi test partial credit?",
        "type": "multiple_select",
        "choices": ["A", "B", "C"],
        "correct_answers": [0, 1]
    }

    # Case 1: None / none -> no partial_credit attribute
    elem_none = build_single_problem_xml(q_data, partial_credit="none")
    cr_none = elem_none.find("choiceresponse")
    assert "partial_credit" not in cr_none.attrib

    # Case 2: halves -> partial_credit="halves"
    elem_halves = build_single_problem_xml(q_data, partial_credit="halves")
    cr_halves = elem_halves.find("choiceresponse")
    assert cr_halves.get("partial_credit") == "halves"

    # Case 3: EDC -> partial_credit="EDC"
    elem_edc = build_single_problem_xml(q_data, partial_credit="EDC")
    cr_edc = elem_edc.find("choiceresponse")
    assert cr_edc.get("partial_credit") == "EDC"


def test_build_single_problem_xml_special_characters():
    question_data = {
        "name": "Cau-Special",
        "question": "Toán tử điều kiện: a < b && c > d & \"hello\"?",
        "type": "multiple_select",
        "choices": ["x < y & z > w", "a == b && c != d", "\"True\" & \"False\""],
        "correct_answers": [0, 2],
        "tags": ["Special&Chars", "Tag<1>"]
    }

    elem = build_single_problem_xml(question_data)
    xml_str = etree.tostring(elem, encoding="utf-8").decode("utf-8")

    # XML must be well-formed and parseable
    reparsed = etree.fromstring(xml_str.encode("utf-8"))
    assert reparsed.tag == "problem"

    cr = reparsed.find("choiceresponse")
    question_p = cr.findall("p")[1]
    assert question_p.text == "Toán tử điều kiện: a < b && c > d & \"hello\"?"

    choices = cr.find("checkboxgroup").findall("choice")
    assert choices[0].text == "x < y & z > w"
    assert choices[2].text == "\"True\" & \"False\""


def test_library_exporter_integration_with_partial_credit():
    exporter = LibraryExporter()
    questions = [
        {
            "name": "Cau-01",
            "question": "Câu 1 đúng 1 đáp án?",
            "type": "multiple_select",
            "choices": ["A", "B", "C"],
            "correct_answers": [0],
            "tags": ["de0"]
        },
        {
            "name": "Cau-02",
            "question": "Câu 2 đúng 2 đáp án?",
            "type": "multiple_select",
            "choices": ["A", "B", "C"],
            "correct_answers": [0, 1],
            "tags": ["de0"]
        }
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        tar_path = os.path.join(tmpdir, "test_lib.tar.gz")
        export_data = {
            "questions": questions,
            "library_name": "Test Parity Library",
            "org": "SoDiTEC",
            "library_code": "TEST_PARITY",
            "start_time": "2030-01-01T00:00:00Z",
            "question_type": "multiple_select",
            "partial_credit": "EDC"
        }

        success = exporter.export(export_data, tar_path)
        assert success is True
        assert os.path.exists(tar_path)

        # Extract and verify XML files inside
        extract_dir = os.path.join(tmpdir, "extracted")
        with tarfile.open(tar_path, "r:gz") as tar:
            tar.extractall(extract_dir)

        problem_dir = os.path.join(extract_dir, "library", "problem")
        xml_files = os.listdir(problem_dir)
        assert len(xml_files) == 2

        for xml_file in xml_files:
            file_path = os.path.join(problem_dir, xml_file)
            tree = etree.parse(file_path)
            root = tree.getroot()
            assert root.tag == "problem"

            cr = root.find("choiceresponse")
            assert cr is not None
            assert cr.get("partial_credit") == "EDC"

            cbg = cr.find("checkboxgroup")
            assert cbg is not None
            assert "shuffle" not in cbg.attrib

            for choice in cbg.findall("choice"):
                assert "fixed" not in choice.attrib
