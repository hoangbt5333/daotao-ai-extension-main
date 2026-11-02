"""
Unit tests for In-Video Quiz (invideoquiz_v2) export and regression testing for main course flow.
Uses lxml to verify strict OLX compliance against the reference fixture.
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

from app.services.export.video_quiz import VideoQuizExporter
from app.services.export.openedx import OpenEdXExporter
from app.services.export.video_quiz_helper import (
    extract_youtube_id,
    parse_timestamp_to_seconds,
    build_invideoquiz_unit,
)
from app.core.exceptions import ExportError


SAMPLE_VIDEO_QUIZ_DATA = {
    "video_title": "Bài giảng Mạng máy tính",
    "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "video_description": "Khảo sát OSPF và đường đi",
    "org": "SoDiTEC",
    "course": "TDC01",
    "run": "2024-May",
    "questions": [
        {
            "id": "7a57198d073f48c3ba4a0eb9436aa15e",
            "name": "Cau-01",
            "question": "Khi kết nối OSPF với hệ thống bên ngoài, default gateway là R. Đúng hay sai?",
            "type": "multiple_choice",
            "choices": ["Đúng", "Sai"],
            "correct_answers": [1],
            "timestamp": "01:00",  # 60 seconds
        },
        {
            "id": "31a440b4e7f34b1a9fd2969a9d426977",
            "name": "Cau-02",
            "question": "Số lượng đường đi đơn xuất phát từ đỉnh 1 đến đỉnh 10 là bao nhiêu?",
            "type": "multiple_choice",
            "choices": ["10", "40320", "362880"],
            "correct_answers": [1],
            "timestamp": "01:30",  # 90 seconds
        }
    ]
}


def test_timestamp_to_seconds_conversion():
    """Verify single canonical timestamp converter."""
    assert parse_timestamp_to_seconds(60) == 60
    assert parse_timestamp_to_seconds("60") == 60
    assert parse_timestamp_to_seconds("01:00") == 60
    assert parse_timestamp_to_seconds("01:30") == 90
    assert parse_timestamp_to_seconds("00:45") == 45
    assert parse_timestamp_to_seconds("01:02:03") == 3723

    with pytest.raises(ValueError):
        parse_timestamp_to_seconds("-10")
    with pytest.raises(ValueError):
        parse_timestamp_to_seconds("abc")
    with pytest.raises(ValueError):
        parse_timestamp_to_seconds("01:00-01:30")  # range not supported in this phase


def test_youtube_id_extraction():
    """Verify YouTube URL extraction and rejection of iframes / drive links."""
    assert extract_youtube_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert extract_youtube_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert extract_youtube_id("https://www.youtube.com/embed/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert extract_youtube_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=10s") == "dQw4w9WgXcQ"

    # Rejections per docs 3.7
    assert extract_youtube_id('<iframe src="https://www.youtube.com/embed/dQw4w9WgXcQ"></iframe>') is None
    assert extract_youtube_id("https://drive.google.com/file/d/123/view") is None
    assert extract_youtube_id("https://vimeo.com/123456") is None
    assert extract_youtube_id("https://example.com/video.mp4") is None


def test_video_quiz_export_structure_and_lxml_validation():
    """
    Test full VideoQuiz export:
    - course/ wrapper
    - invideoquiz_v2 tag and attributes in vertical
    - video_id matching <video url_name> and course/video/{id}.xml
    - problem files existence and matching IDs
    - timemap JSON parsing
    - advanced_modules containing invideoquiz_v2 in course.xml and policy.json
    - no transcript_* clutter
    """
    exporter = VideoQuizExporter()
    with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp_file:
        tmp_tar_path = tmp_file.name

    try:
        ok = exporter.export(SAMPLE_VIDEO_QUIZ_DATA, tmp_tar_path)
        assert ok is True

        with open(tmp_tar_path, "rb") as f:
            tar_bytes = f.read()

        with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode="r:gz") as tar:
            members = tar.getnames()

            # 1. Assert course/ wrapper is present on all files
            assert all(m.startswith("course/") or m == "course" for m in members)

            # 2. Assert course descriptor and policy files
            assert "course/course.xml" in members
            assert "course/course/2024-May.xml" in members
            assert "course/policies/2024-May/policy.json" in members

            # Check advanced_modules in course/course/2024-May.xml
            run_xml_content = tar.extractfile("course/course/2024-May.xml").read().decode("utf-8")
            run_root = etree.fromstring(run_xml_content.encode("utf-8"))
            adv_mods_attr = run_root.get("advanced_modules")
            assert adv_mods_attr is not None
            assert "invideoquiz_v2" in json.loads(adv_mods_attr)

            # Check advanced_modules in policy.json
            policy_json_content = tar.extractfile("course/policies/2024-May/policy.json").read().decode("utf-8")
            policy_data = json.loads(policy_json_content)
            assert "course/2024-May" in policy_data
            assert "invideoquiz_v2" in policy_data["course/2024-May"]["advanced_modules"]

            # 3. Find vertical XML
            vertical_files = [m for m in members if m.startswith("course/vertical/") and m.endswith(".xml")]
            assert len(vertical_files) == 1
            vert_name = vertical_files[0]

            vert_content = tar.extractfile(vert_name).read().decode("utf-8")
            vert_root = etree.fromstring(vert_content.encode("utf-8"))
            assert vert_root.tag == "vertical"

            # Check <video> in vertical
            video_elems = vert_root.findall("video")
            assert len(video_elems) == 1
            video_url_name = video_elems[0].get("url_name")
            assert video_url_name is not None
            assert len(video_url_name) == 32

            # Check video file exists and matches
            video_file = f"course/video/{video_url_name}.xml"
            assert video_file in members

            video_content = tar.extractfile(video_file).read().decode("utf-8")
            video_root = etree.fromstring(video_content.encode("utf-8"))
            assert video_root.tag == "video"
            assert video_root.get("url_name") == video_url_name
            assert video_root.get("youtube") == "1.00:dQw4w9WgXcQ"
            assert video_root.get("youtube_id_1_0") == "dQw4w9WgXcQ"
            # Ensure no transcript_* garbage
            assert not any(k.startswith("transcript_available_translations_json_text_") for k in video_root.attrib)

            # 4. Check <invideoquiz_v2> in vertical
            quiz_elems = vert_root.findall("invideoquiz_v2")
            assert len(quiz_elems) == 1
            quiz_elem = quiz_elems[0]
            assert quiz_elem.get("xblock-family") == "xblock.v1"
            assert quiz_elem.get("video_id") == video_url_name

            # Check timemap
            timemap_str = quiz_elem.get("timemap")
            assert timemap_str is not None
            timemap = json.loads(timemap_str)
            assert set(timemap.keys()) == {"60", "90"}
            assert timemap["60"] == "7a57198d073f48c3ba4a0eb9436aa15e"
            assert timemap["90"] == "31a440b4e7f34b1a9fd2969a9d426977"

            # 5. Check problems in vertical and in course/problem/
            prob_elems = vert_root.findall("problem")
            assert len(prob_elems) == 2
            assert prob_elems[0].get("url_name") == "7a57198d073f48c3ba4a0eb9436aa15e"
            assert prob_elems[1].get("url_name") == "31a440b4e7f34b1a9fd2969a9d426977"

            for pid in ["7a57198d073f48c3ba4a0eb9436aa15e", "31a440b4e7f34b1a9fd2969a9d426977"]:
                pfile = f"course/problem/{pid}.xml"
                assert pfile in members
                p_content = tar.extractfile(pfile).read().decode("utf-8")
                p_root = etree.fromstring(p_content.encode("utf-8"))
                assert p_root.tag == "problem"

    finally:
        Path(tmp_tar_path).unlink(missing_ok=True)


def test_video_quiz_rejects_invalid_urls():
    """Verify that iframes, Drive links, and non-YouTube links are rejected."""
    exporter = VideoQuizExporter()
    with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp_file:
        tmp_tar_path = tmp_file.name

    try:
        # 1. Test iframe rejection
        data_iframe = dict(SAMPLE_VIDEO_QUIZ_DATA)
        data_iframe["video_url"] = '<iframe src="https://www.youtube.com/embed/dQw4w9WgXcQ"></iframe>'
        with pytest.raises(ExportError) as exc_info:
            exporter.export(data_iframe, tmp_tar_path)
        assert "không áp dụng với iframe/raw HTML theo mục 3.7" in str(exc_info.value)

        # 2. Test Google Drive rejection
        data_drive = dict(SAMPLE_VIDEO_QUIZ_DATA)
        data_drive["video_url"] = "https://drive.google.com/file/d/123/view"
        with pytest.raises(ExportError) as exc_info:
            exporter.export(data_drive, tmp_tar_path)
        assert "không áp dụng với iframe/raw HTML theo mục 3.7" in str(exc_info.value)

        # 3. Test non-YouTube domain rejection
        data_vimeo = dict(SAMPLE_VIDEO_QUIZ_DATA)
        data_vimeo["video_url"] = "https://vimeo.com/123456"
        with pytest.raises(ExportError) as exc_info:
            exporter.export(data_vimeo, tmp_tar_path)
        assert "không áp dụng với iframe/raw HTML theo mục 3.7" in str(exc_info.value)

    finally:
        Path(tmp_tar_path).unlink(missing_ok=True)


def test_video_quiz_rejects_duplicate_timestamps():
    """Verify that duplicate timestamps are rejected."""
    exporter = VideoQuizExporter()
    with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp_file:
        tmp_tar_path = tmp_file.name

    try:
        data_dup = dict(SAMPLE_VIDEO_QUIZ_DATA)
        data_dup["questions"] = [
            {
                "question": "Câu 1",
                "choices": ["A", "B"],
                "correct_answers": [0],
                "timestamp": "01:00",  # 60s
            },
            {
                "question": "Câu 2",
                "choices": ["C", "D"],
                "correct_answers": [1],
                "timestamp": "60",     # Also 60s!
            }
        ]
        with pytest.raises(ExportError) as exc_info:
            exporter.export(data_dup, tmp_tar_path)
        assert "trùng lặp" in str(exc_info.value)
        assert "60" in str(exc_info.value)

    finally:
        Path(tmp_tar_path).unlink(missing_ok=True)


def test_regression_main_course_export():
    """Verify that OpenEdXExporter continues to work without regression."""
    exporter = OpenEdXExporter()
    with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp_file:
        tmp_tar_path = tmp_file.name

    try:
        main_course_data = {
            "outline": [
                {
                    "title": "Chương 1",
                    "subsections": [
                        {
                            "title": "Bài 1",
                            "units": [
                                {
                                    "title": "Đơn vị Text",
                                    "type": "text",
                                    "content": "<p>Nội dung bài học</p>"
                                },
                                {
                                    "title": "Đơn vị Video",
                                    "type": "video",
                                    "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
                                }
                            ]
                        }
                    ]
                }
            ],
            "questions": [],
            "uploaded_assets": []
        }

        ok = exporter.export(main_course_data, tmp_tar_path)
        assert ok is True

        with open(tmp_tar_path, "rb") as f:
            tar_bytes = f.read()

        with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode="r:gz") as tar:
            members = tar.getnames()
            assert any(m.startswith("course/") for m in members)
            assert "course/course.xml" in members
            
            # Check video xml created properly
            video_files = [m for m in members if m.startswith("course/video/") and m.endswith(".xml")]
            assert len(video_files) == 1
            v_content = tar.extractfile(video_files[0]).read().decode("utf-8")
            v_root = etree.fromstring(v_content.encode("utf-8"))
            assert v_root.get("youtube") == "1.00:dQw4w9WgXcQ"
            assert v_root.get("youtube_id_1_0") == "dQw4w9WgXcQ"

    finally:
        Path(tmp_tar_path).unlink(missing_ok=True)


def test_problem_xml_child_elements_not_escaped():
    """
    FAILING TEST:
    Assert that <problem> XML has real XML child elements (not escaped strings in .text),
    contains no '&lt;', has empty/whitespace problem.text, and matches reference structure.
    """
    exporter = VideoQuizExporter()
    with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp_file:
        tmp_tar_path = tmp_file.name

    try:
        ok = exporter.export(SAMPLE_VIDEO_QUIZ_DATA, tmp_tar_path)
        assert ok is True

        with open(tmp_tar_path, "rb") as f:
            tar_bytes = f.read()

        with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode="r:gz") as tar:
            prob_files = [m for m in tar.getnames() if m.startswith("course/problem/") and m.endswith(".xml")]
            assert len(prob_files) == 2

            for pfile in prob_files:
                raw_xml = tar.extractfile(pfile).read().decode("utf-8")

                # 1. Assert file does NOT contain escaped tags
                assert "&lt;p" not in raw_xml, f"Found '&lt;p' in {pfile}: content was escaped!"
                assert "&lt;multiplechoiceresponse" not in raw_xml, f"Found '&lt;multiplechoiceresponse' in {pfile}: content was escaped!"
                assert "&lt;choicegroup" not in raw_xml, f"Found '&lt;choicegroup' in {pfile}: content was escaped!"

                # 2. Parse with lxml and assert real child elements
                root = etree.fromstring(raw_xml.encode("utf-8"))
                assert root.tag == "problem"

                # problem.text must be None or only whitespace
                text = (root.text or "").strip()
                assert text == "", f"problem.text is not empty (it contains raw text): {text!r}"

                # Must have actual child element multiplechoiceresponse
                mcr = root.find("multiplechoiceresponse")
                assert mcr is not None, f"Root <problem> has no child element <multiplechoiceresponse> in {pfile}"

                # Child elements of multiplechoiceresponse: p and choicegroup
                p_elem = mcr.find("p")
                assert p_elem is not None, f"No <p> element found inside <multiplechoiceresponse> in {pfile}"
                assert (p_elem.text or "").strip() != "", f"<p> text is empty in {pfile}"

                cg = mcr.find("choicegroup")
                assert cg is not None, f"No <choicegroup> element found inside <multiplechoiceresponse> in {pfile}"
                assert cg.get("type") == "MultipleChoice"

                choices = cg.findall("choice")
                assert len(choices) >= 2, f"Expected at least 2 <choice> elements, found {len(choices)}"
                for c in choices:
                    assert c.get("correct") in ("true", "false")
                    assert (c.text or "").strip() != ""

    finally:
        Path(tmp_tar_path).unlink(missing_ok=True)


def test_compare_structure_with_reference_fixture():
    """
    Compare problem XML structure with the reference fixture from Studio:
    backend/tests/fixtures/reference/course.quiz_in_video.tar.gz.
    """
    ref_tar_path = Path(BACKEND) / "tests" / "fixtures" / "reference" / "course.quiz_in_video.tar.gz"
    if not ref_tar_path.exists():
        pytest.skip("Reference fixture not found")

    with tarfile.open(ref_tar_path, "r:gz") as ref_tar:
        ref_prob_names = [m for m in ref_tar.getnames() if "problem" in m and m.endswith(".xml")]
        assert len(ref_prob_names) > 0
        ref_content = ref_tar.extractfile(ref_prob_names[0]).read()
        ref_root = etree.fromstring(ref_content)

        # Reference has <multiplechoiceresponse> as direct child of <problem>
        assert ref_root.tag == "problem"
        ref_mcr = ref_root.find("multiplechoiceresponse")
        assert ref_mcr is not None
        ref_cg = ref_mcr.find("choicegroup")
        assert ref_cg is not None
        assert ref_cg.get("type") == "MultipleChoice"

        # Export our video quiz and verify exact structural match
        exporter = VideoQuizExporter()
        with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp_file:
            tmp_tar_path = tmp_file.name
        try:
            exporter.export(SAMPLE_VIDEO_QUIZ_DATA, tmp_tar_path)
            with tarfile.open(tmp_tar_path, "r:gz") as tar:
                our_prob_names = [m for m in tar.getnames() if m.startswith("course/problem/") and m.endswith(".xml")]
                our_content = tar.extractfile(our_prob_names[0]).read()
                our_root = etree.fromstring(our_content)

                # Tag names and hierarchy must match reference
                assert our_root.tag == ref_root.tag == "problem"
                our_mcr = our_root.find("multiplechoiceresponse")
                assert our_mcr is not None, "our_root missing multiplechoiceresponse"
                our_cg = our_mcr.find("choicegroup")
                assert our_cg is not None, "our_mcr missing choicegroup"
                assert our_cg.get("type") == ref_cg.get("type") == "MultipleChoice"
                assert (our_root.text or "").strip() == (ref_root.text or "").strip() == ""
        finally:
            Path(tmp_tar_path).unlink(missing_ok=True)
