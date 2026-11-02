"""
TDD Tests for problem markdown roundtrip and OLX XML parity with Studio Simple Editor.

Verifies:
1. Structural and markdown parity with reference fixtures (library.mau_chuan.tar.gz):
   - Câu 01: multiple_choice with question text, shuffle (!) trigger, ( ), (x)
   - Câu 02: multiple_choice without question text, (!x), (@) fixed choice
   - Câu 03: multiple_select with question text, [x], [ ]
2. Markdown attribute cleanliness:
   - Real newlines (\n), NO "&#10;" string, NO double-escaped "&amp;#10;" in raw XML
   - NO "<p/>", NO "=====", NO ">>...<<" markers, NO "||"
   - Wrong choices strictly "( )" with whitespace (never "()")
3. Marker and attribute rules:
   - shuffle="true" and (!) / (!x) ONLY when question has shuffle
   - fixed="true" and (@) / (@x) ONLY when choice is in fixed_choices
   - multiple_select: always [x] and [ ], never ! or @, never shuffle on checkboxgroup, never fixed on choice
   - partial_credit preserved on <choiceresponse>
4. Special characters (&, <, >, ") and Vietnamese diacritics
5. End-to-end LibraryExporter .tar.gz generation and raw byte verification
"""
import os
import sys
import tarfile
import tempfile
from pathlib import Path
from lxml import etree
import pytest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.services.export.helpers import create_markdown_content, build_single_problem_xml
from app.services.export.library import LibraryExporter


REF_DIR = BACKEND / "tests" / "fixtures" / "reference"
MAU_CHUAN_TAR = REF_DIR / "library.mau_chuan.tar.gz"


def _extract_reference_problems():
    """Extract and parse problem XMLs from library.mau_chuan.tar.gz."""
    problems = {}
    with tarfile.open(MAU_CHUAN_TAR, "r:gz") as tar:
        for m in tar.getmembers():
            if m.name.endswith(".xml") and "problem" in m.name:
                f = tar.extractfile(m)
                content = f.read().decode("utf-8")
                root = etree.fromstring(content.encode("utf-8"))
                dname = root.get("display_name")
                problems[dname] = {
                    "raw_xml": content,
                    "root": root,
                    "markdown": root.get("markdown"),
                }
    return problems


# ============================================================================
# 1. Structural and markdown parity with reference fixture (library.mau_chuan)
# ============================================================================

def test_parity_with_mau_chuan_cau_01():
    """
    Câu 01 in library.mau_chuan.tar.gz:
    Multiple choice with question text, shuffle trigger (!), ( ), (x).
    Expected markdown:
      Câu hỏi mẫu 01:\n(!) sai 1\n( ) sai 2\n(x) đúng\n
    Expected XML:
      <problem display_name="Câu 01" markdown="..." tags="[&quot;M\u1eabu chu\u1ea9n&quot;]">
        <multiplechoiceresponse>
          <p>Câu hỏi mẫu 01:</p>
          <choicegroup type="MultipleChoice" shuffle="true">
            <choice correct="false">sai 1</choice>
            <choice correct="false">sai 2</choice>
            <choice correct="true">đúng</choice>
          </choicegroup>
        </multiplechoiceresponse>
      </problem>
    """
    ref_problems = _extract_reference_problems()
    assert "Câu 01" in ref_problems
    ref_01 = ref_problems["Câu 01"]

    q_data = {
        "name": "Câu 01",
        "question": "Câu hỏi mẫu 01:",
        "type": "multiple_choice",
        "choices": ["sai 1", "sai 2", "đúng"],
        "correct_answers": [2],
        "fixed_choices": [],
        "shuffle": True,
        "tags": ["Mẫu chuẩn"]
    }

    # Verify markdown
    md = create_markdown_content(q_data)
    assert md == ref_01["markdown"]

    # Verify XML
    elem = build_single_problem_xml(q_data, display_name="Câu 01")
    xml_str = etree.tostring(elem, encoding="utf-8", pretty_print=True).decode("utf-8")

    # Check tags & hierarchy
    mcr = elem.find("multiplechoiceresponse")
    assert mcr is not None
    # Must use <p>, not <label>, no empty <p/>
    p_tags = mcr.findall("p")
    assert len(p_tags) == 1
    assert p_tags[0].text == "Câu hỏi mẫu 01:"
    assert mcr.find("label") is None

    cg = mcr.find("choicegroup")
    assert cg is not None
    assert cg.get("type") == "MultipleChoice"
    assert cg.get("shuffle") == "true"

    choices = cg.findall("choice")
    assert len(choices) == 3
    assert choices[0].get("correct") == "false" and choices[0].text == "sai 1"
    assert choices[1].get("correct") == "false" and choices[1].text == "sai 2"
    assert choices[2].get("correct") == "true" and choices[2].text == "đúng"


def test_parity_with_mau_chuan_cau_02():
    """
    Câu 02 in library.mau_chuan.tar.gz:
    Multiple choice without question text, shuffle trigger (!x) on correct answer,
    fixed choice (@) at end.
    Expected markdown:
      (!x) đúng\n( ) sai 2\n( ) sai 1\n(@) tất cả
    Expected XML:
      <problem display_name="Câu 02" markdown="..." tags="[&quot;M\u1eabu chu\u1ea9n&quot;]">
        <multiplechoiceresponse>
          <choicegroup type="MultipleChoice" shuffle="true">
            <choice correct="true">đúng</choice>
            <choice correct="false">sai 2</choice>
            <choice correct="false">sai 1</choice>
            <choice correct="false" fixed="true">tất cả</choice>
          </choicegroup>
        </multiplechoiceresponse>
      </problem>
    """
    ref_problems = _extract_reference_problems()
    assert "Câu 02" in ref_problems
    ref_02 = ref_problems["Câu 02"]

    q_data = {
        "name": "Câu 02",
        "question": "",
        "type": "multiple_choice",
        "choices": ["đúng", "sai 2", "sai 1", "tất cả"],
        "correct_answers": [0],
        "fixed_choices": [3],
        "shuffle": True,
        "tags": ["Mẫu chuẩn"]
    }

    # Verify markdown
    md = create_markdown_content(q_data).strip()
    assert md == ref_02["markdown"].strip()

    # Verify XML
    elem = build_single_problem_xml(q_data, display_name="Câu 02")
    mcr = elem.find("multiplechoiceresponse")
    assert mcr is not None
    # When question is empty, no <p> element
    assert len(mcr.findall("p")) == 0
    assert mcr.find("label") is None

    cg = mcr.find("choicegroup")
    assert cg is not None
    assert cg.get("shuffle") == "true"

    choices = cg.findall("choice")
    assert len(choices) == 4
    assert choices[0].get("correct") == "true"
    assert choices[1].get("correct") == "false"
    assert choices[2].get("correct") == "false"
    assert choices[3].get("correct") == "false" and choices[3].get("fixed") == "true"


def test_parity_with_mau_chuan_cau_03():
    """
    Câu 03 in library.mau_chuan.tar.gz:
    Multiple select (checkbox) with question text.
    Expected markdown:
      Câu hỏi mẫu nhiều đáp án?\n[x] đúng\n[ ] incorrect\n[x] correct\n
    Expected XML:
      <problem display_name="Câu 03" markdown="..." tags="[&quot;M\u1eabu chu\u1ea9n&quot;]">
        <choiceresponse>
          <p>Câu hỏi mẫu nhiều đáp án?</p>
          <checkboxgroup>
            <choice correct="true">đúng</choice>
            <choice correct="false">incorrect</choice>
            <choice correct="true">correct</choice>
          </checkboxgroup>
        </choiceresponse>
      </problem>
    """
    ref_problems = _extract_reference_problems()
    assert "Câu 03" in ref_problems
    ref_03 = ref_problems["Câu 03"]

    q_data = {
        "name": "Câu 03",
        "question": "Câu hỏi mẫu nhiều đáp án?",
        "type": "multiple_select",
        "choices": ["đúng", "incorrect", "correct"],
        "correct_answers": [0, 2],
        "tags": ["Mẫu chuẩn"]
    }

    # Verify markdown
    md = create_markdown_content(q_data)
    assert md == ref_03["markdown"]

    # Verify XML
    elem = build_single_problem_xml(q_data, display_name="Câu 03")
    cr = elem.find("choiceresponse")
    assert cr is not None
    p_tags = cr.findall("p")
    assert len(p_tags) == 1
    assert p_tags[0].text == "Câu hỏi mẫu nhiều đáp án?"
    assert cr.find("label") is None

    cbg = cr.find("checkboxgroup")
    assert cbg is not None
    assert "shuffle" not in cbg.attrib

    choices = cbg.findall("choice")
    assert len(choices) == 3
    assert choices[0].get("correct") == "true"
    assert choices[1].get("correct") == "false"
    assert choices[2].get("correct") == "true"
    for c in choices:
        assert "fixed" not in c.attrib


# ============================================================================
# 2. Markdown attribute cleanliness (no &#10;, no <p/>, no =====, no >>...<<)
# ============================================================================

def test_markdown_attribute_cleanliness_and_real_newlines():
    """Verify markdown content in element attribute has real newlines and no dirty strings."""
    q_data = {
        "name": "Cau-Clean",
        "question": "Câu hỏi kiểm tra sạch markdown?",
        "type": "multiple_choice",
        "choices": ["Đáp án A", "Đáp án B", "Đáp án C"],
        "correct_answers": [1],
        "shuffle": False
    }

    elem = build_single_problem_xml(q_data)
    md_attr = elem.get("markdown")

    # 1. Must NOT contain literal &#10; or &amp;#10; in the DOM string
    assert "&#10;" not in md_attr
    assert "&amp;#10;" not in md_attr

    # 2. Must NOT contain <p/>, =====, or >>...<<
    assert "<p/>" not in md_attr
    assert "<p>" not in md_attr
    assert "=====" not in md_attr
    assert ">>" not in md_attr
    assert "<<" not in md_attr
    assert "||" not in md_attr

    # 3. Must contain real newlines
    assert "\n" in md_attr
    lines = [l for l in md_attr.split("\n") if l]
    assert len(lines) == 4
    assert lines[0] == "Câu hỏi kiểm tra sạch markdown?"
    assert lines[1] == "( ) Đáp án A"
    assert lines[2] == "(x) Đáp án B"
    assert lines[3] == "( ) Đáp án C"

    # 4. In serialized XML bytes: newlines must be encoded as single &#10;, NEVER &amp;#10;
    xml_bytes = etree.tostring(elem, encoding="utf-8")
    assert b"&amp;#10;" not in xml_bytes
    assert b"&#10;" in xml_bytes


# ============================================================================
# 3. Marker & Attribute rules: shuffle and fixed
# ============================================================================

def test_shuffle_rule_only_when_has_shuffle():
    """
    shuffle="true" and (!) / (!x) ONLY when question has shuffle=True.
    When shuffle=False, choicegroup must NOT have shuffle attribute,
    and first choice must use regular ( ) or (x).
    """
    # Case A: shuffle=False
    q_no_shuffle = {
        "question": "Câu không shuffle",
        "type": "multiple_choice",
        "choices": ["Sai 1", "Đúng", "Sai 2"],
        "correct_answers": [1],
        "shuffle": False
    }
    elem_no = build_single_problem_xml(q_no_shuffle)
    cg_no = elem_no.find(".//choicegroup")
    assert "shuffle" not in cg_no.attrib
    md_no = elem_no.get("markdown")
    assert "(!)" not in md_no
    assert "(!x)" not in md_no
    assert "( ) Sai 1\n(x) Đúng\n( ) Sai 2" in md_no

    # Case B: shuffle=True, first answer wrong
    q_shuffle_wrong_first = {
        "question": "Câu có shuffle",
        "type": "multiple_choice",
        "choices": ["Sai 1", "Đúng", "Sai 2"],
        "correct_answers": [1],
        "shuffle": True
    }
    elem_shuf = build_single_problem_xml(q_shuffle_wrong_first)
    cg_shuf = elem_shuf.find(".//choicegroup")
    assert cg_shuf.get("shuffle") == "true"
    md_shuf = elem_shuf.get("markdown")
    assert "(!) Sai 1" in md_shuf

    # Case C: shuffle=True, first answer correct
    q_shuffle_correct_first = {
        "question": "Câu có shuffle đúng đầu",
        "type": "multiple_choice",
        "choices": ["Đúng", "Sai 1", "Sai 2"],
        "correct_answers": [0],
        "shuffle": True
    }
    elem_shuf_c = build_single_problem_xml(q_shuffle_correct_first)
    md_shuf_c = elem_shuf_c.get("markdown")
    assert "(!x) Đúng" in md_shuf_c


def test_fixed_rule_only_when_in_fixed_choices():
    """
    fixed="true" and (@) / (@x) ONLY when choice is in fixed_choices.
    """
    q_fixed = {
        "question": "Câu có fixed",
        "type": "multiple_choice",
        "choices": ["A", "B", "Tất cả sai", "Tất cả đúng"],
        "correct_answers": [3],
        "fixed_choices": [2, 3],
        "shuffle": True
    }
    elem = build_single_problem_xml(q_fixed)
    choices = elem.findall(".//choice")
    assert "fixed" not in choices[0].attrib
    assert "fixed" not in choices[1].attrib
    assert choices[2].get("fixed") == "true"
    assert choices[3].get("fixed") == "true"

    md = elem.get("markdown")
    assert "(!) A" in md
    assert "( ) B" in md
    assert "(@) Tất cả sai" in md
    assert "(@x) Tất cả đúng" in md


def test_multiple_select_never_has_shuffle_or_fixed():
    """
    Multiple select MUST NEVER have ! or @ in markdown,
    and NEVER have shuffle on checkboxgroup or fixed on choice in XML.
    """
    q_data = {
        "question": "Câu nhiều đáp án",
        "type": "multiple_select",
        "choices": ["A", "B", "C"],
        "correct_answers": [0, 2],
        "fixed_choices": [2],  # Must be ignored
        "shuffle": True,        # Must be ignored
        "partial_credit": "halves"
    }
    elem = build_single_problem_xml(q_data)
    cr = elem.find("choiceresponse")
    assert cr.get("partial_credit") == "halves"

    cbg = cr.find("checkboxgroup")
    assert "shuffle" not in cbg.attrib
    for c in cbg.findall("choice"):
        assert "fixed" not in c.attrib

    md = elem.get("markdown")
    assert "!" not in md
    assert "@" not in md
    assert "[x] A\n[ ] B\n[x] C\n" in md


def test_wrong_choice_always_has_space():
    """Wrong choices MUST ALWAYS be '( )' with space, never '()'."""
    q_data = {
        "question": "Test space",
        "type": "multiple_choice",
        "choices": ["Sai", "Đúng"],
        "correct_answers": [1],
        "shuffle": False
    }
    md = create_markdown_content(q_data)
    assert "( ) Sai" in md
    assert "() Sai" not in md


# ============================================================================
# 4. Special characters (&, <, >, ") and Vietnamese diacritics
# ============================================================================

def test_special_characters_and_vietnamese_roundtrip():
    """Verify special XML chars and Vietnamese survive roundtrip without corruption."""
    q_data = {
        "name": "Câu đặc biệt: a < b & c > d",
        "question": "Toán tử: a < b && c > d & \"chuẩn\"? Tiếng Việt: Đề thi môn Lý - Hóa!",
        "type": "multiple_choice",
        "choices": [
            "Phương án <A> & 'đúng'",
            "Phương án >B< & \"sai\"",
            "Tất cả đều đúng & hợp lệ"
        ],
        "correct_answers": [0],
        "fixed_choices": [2],
        "shuffle": True,
        "tags": ["Toán & Lý", "Đề số <01>"]
    }

    elem = build_single_problem_xml(q_data)
    xml_bytes = etree.tostring(elem, encoding="utf-8", pretty_print=True)

    # Reparse with lxml
    root = etree.fromstring(xml_bytes)
    assert root.tag == "problem"
    assert root.get("display_name") == "Câu đặc biệt: a < b & c > d"

    p = root.find(".//p")
    assert p.text == "Toán tử: a < b && c > d & \"chuẩn\"? Tiếng Việt: Đề thi môn Lý - Hóa!"

    choices = root.findall(".//choice")
    assert choices[0].text == "Phương án <A> & 'đúng'"
    assert choices[1].text == "Phương án >B< & \"sai\""
    assert choices[2].text == "Tất cả đều đúng & hợp lệ"

    md = root.get("markdown")
    assert "Toán tử: a < b && c > d & \"chuẩn\"? Tiếng Việt: Đề thi môn Lý - Hóa!" in md
    assert "(!x) Phương án <A> & 'đúng'" in md
    assert "( ) Phương án >B< & \"sai\"" in md
    assert "(@) Tất cả đều đúng & hợp lệ" in md


# ============================================================================
# 5. Full LibraryExporter integration and raw byte verification
# ============================================================================

def test_full_library_exporter_tar_gz_raw_bytes():
    """Export an actual tar.gz library package and inspect the raw XML bytes inside."""
    exporter = LibraryExporter()
    questions = [
        {
            "name": "Câu 01",
            "question": "Câu hỏi mẫu 01:",
            "type": "multiple_choice",
            "choices": ["sai 1", "sai 2", "đúng"],
            "correct_answers": [2],
            "fixed_choices": [],
            "shuffle": True,
            "tags": ["Mẫu chuẩn"]
        },
        {
            "name": "Câu 02",
            "question": "",
            "type": "multiple_choice",
            "choices": ["đúng", "sai 2", "sai 1", "tất cả"],
            "correct_answers": [0],
            "fixed_choices": [3],
            "shuffle": True,
            "tags": ["Mẫu chuẩn"]
        },
        {
            "name": "Câu 03",
            "question": "Câu hỏi mẫu nhiều đáp án?",
            "type": "multiple_select",
            "choices": ["đúng", "incorrect", "correct"],
            "correct_answers": [0, 2],
            "partial_credit": "EDC",
            "tags": ["Mẫu chuẩn"]
        }
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        tar_path = os.path.join(tmpdir, "library_export_sample.tar.gz")
        data = {
            "questions": questions,
            "library_name": "Thư viện mẫu chuẩn",
            "org": "SoDiTEC",
            "library_code": "LIB_SAMPLE",
            "start_time": "2030-01-01T00:00:00Z"
        }

        success = exporter.export(data, tar_path)
        assert success is True
        assert os.path.exists(tar_path)

        # Inspect raw bytes in tar.gz
        with tarfile.open(tar_path, "r:gz") as tar:
            prob_members = [m for m in tar.getmembers() if m.name.endswith(".xml") and "problem" in m.name]
            assert len(prob_members) == 3

            for m in prob_members:
                raw_bytes = tar.extractfile(m).read()
                # 1. NO &amp;#10; (must not be double-escaped)
                assert b"&amp;#10;" not in raw_bytes
                # 2. NO <p/> (no redundant empty tags)
                assert b"<p/>" not in raw_bytes
                assert b"&lt;p/&gt;" not in raw_bytes
                # 3. NO =====
                assert b"=====" not in raw_bytes
                # 4. NO >>...<<
                assert b"&gt;&gt;" not in raw_bytes
                assert b">>" not in raw_bytes
                # 5. NO old instructions
                assert "Chọn 1 đáp án đúng".encode("utf-8") not in raw_bytes
                assert "Chọn tất cả đáp án đúng".encode("utf-8") not in raw_bytes
