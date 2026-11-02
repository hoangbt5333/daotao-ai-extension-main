"""
Structural integrity tests for question XML generation across all export flows:
1. VideoQuizExporter (fixed via build_single_problem_xml)
2. LibraryExporter
3. OpenEdXExporter (_create_problem_xml / _create_problems_from_questions)
"""
import io
import json
import sys
import tarfile
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import pytest
from lxml import etree

from app.services.export.library import LibraryExporter
from app.services.export.openedx import OpenEdXExporter


def test_library_exporter_problem_structure():
    """Verify that LibraryExporter generates real XML child elements (not escaped strings in .text)."""
    exporter = LibraryExporter()
    with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp_file:
        tmp_tar_path = tmp_file.name

    try:
        data = {
            "library_name": "Test Library",
            "library_code": "LIB01",
            "org": "SoDiTEC",
            "questions": [
                {
                    "name": "Cau-01",
                    "question": "Câu hỏi trắc nghiệm một đáp án?",
                    "type": "multiple_choice",
                    "choices": ["Đáp án A", "Đáp án B"],
                    "correct_answers": [0],
                    "tags": ["chuong1", "de0"]
                },
                {
                    "name": "Cau-02",
                    "question": "Câu hỏi trắc nghiệm nhiều đáp án?",
                    "type": "multiple_select",
                    "choices": ["Lựa chọn 1", "Lựa chọn 2", "Lựa chọn 3"],
                    "correct_answers": [0, 2],
                    "tags": ["chuong1"]
                }
            ]
        }

        ok = exporter.export(data, tmp_tar_path)
        assert ok is True

        with tarfile.open(tmp_tar_path, "r:gz") as tar:
            prob_files = [m for m in tar.getnames() if m.startswith("library/problem/") and m.endswith(".xml")]
            assert len(prob_files) == 2

            for pfile in prob_files:
                raw_xml = tar.extractfile(pfile).read().decode("utf-8")
                root = etree.fromstring(raw_xml.encode("utf-8"))
                assert root.tag == "problem"

                # problem.text must be None or only whitespace (no markup inside text)
                assert (root.text or "").strip() == ""

                # Root must have real child element (either multiplechoiceresponse or choiceresponse)
                mcr = root.find("multiplechoiceresponse")
                cr = root.find("choiceresponse")
                assert (mcr is not None) or (cr is not None), f"Missing real response element in {pfile}"

                if mcr is not None:
                    cg = mcr.find("choicegroup")
                    assert cg is not None
                    assert len(cg.findall("choice")) >= 2
                if cr is not None:
                    cbg = cr.find("checkboxgroup")
                    assert cbg is not None
                    assert len(cbg.findall("choice")) >= 2

    finally:
        Path(tmp_tar_path).unlink(missing_ok=True)


def test_openedx_exporter_has_escaping_bug():
    """
    Test and document that OpenEdXExporter currently has the XML escaping bug:
    _create_problem_xml assigns problem_elem.text = html_content,
    causing <multiplechoiceresponse> to become escaped text instead of an element.
    """
    exporter = OpenEdXExporter()
    with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp_file:
        tmp_tar_path = tmp_file.name

    try:
        data = {
            "outline": [
                {
                    "title": "Chương 1",
                    "subsections": [
                        {
                            "title": "Bài 1",
                            "units": [{"title": "Unit 1", "type": "text", "content": "Text"}]
                        }
                    ]
                }
            ],
            "questions": [
                {
                    "name": "Cau-01",
                    "question": "Câu hỏi trắc nghiệm?",
                    "type": "multiple_choice",
                    "choices": ["A", "B"],
                    "correct_answers": [0],
                    "tags": ["tag1"]
                }
            ],
            "uploaded_assets": []
        }

        ok = exporter.export(data, tmp_tar_path)
        assert ok is True

        with tarfile.open(tmp_tar_path, "r:gz") as tar:
            prob_files = [m for m in tar.getnames() if m.startswith("course/problem/") and m.endswith(".xml")]
            assert len(prob_files) == 1
            raw_xml = tar.extractfile(prob_files[0]).read().decode("utf-8")

            # Documenting the known bug:
            # OpenEdXExporter escapes tags into &lt;multiplechoiceresponse
            is_buggy_escaped = "&lt;multiplechoiceresponse" in raw_xml
            assert is_buggy_escaped is True, "OpenEdXExporter is expected to have the escaping bug before being fixed"

            root = etree.fromstring(raw_xml.encode("utf-8"))
            # Because it is escaped, root has NO child elements!
            assert root.find("multiplechoiceresponse") is None
            assert len(root) == 0

    finally:
        Path(tmp_tar_path).unlink(missing_ok=True)
