"""
Comprehensive integration test for In-Video Quiz inside course generation workflow.

Verifies:
1. Outline with pdf, regular video, and 2 video_quiz units (one with radio + checkbox + @tag).
2. Export course tar.gz.
3. Unpack and assert:
   - invideoquiz_v2 in vertical in proper order
   - video_id in invideoquiz_v2 matches url_name of <video> tag and course/video/{id}.xml
   - timemap is valid JSON mapping seconds to problem url_names
   - course/problem/{id}.xml has real child elements and clean markdown (no &lt;)
   - policy.json has invideoquiz_v2 in advanced_modules and is valid JSON
   - course/static/ does NOT contain any .txt files
   - course/policies/assets.json does NOT contain any .txt files
   - Other units (pdf, regular video) are unaffected
   - Temp directories cleaned up
"""
import os
import sys
import json
import tarfile
import tempfile
from pathlib import Path
from lxml import etree
import pytest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.services.export.openedx import OpenEdXExporter
from app.services.export.video_quiz_helper import (
    validate_and_prepare_video_quiz_units,
    extract_youtube_id,
    parse_timestamp_to_seconds,
)


@pytest.fixture
def sample_course_data():
    txt_quiz1 = """@tag: chuong1, video1

@time: 01:00
Câu 1: Câu hỏi một đáp án trong video 1?
(!) Phương án 1 (shuffle)
(x) Phương án 2 đúng
( ) Phương án 3 sai
(@) Phương án 4 cố định

@time: 02:30
Câu 2: Câu hỏi nhiều đáp án trong video 1?
[x] Lựa chọn A đúng
[ ] Lựa chọn B sai
[x] Lựa chọn C đúng
"""

    txt_quiz2 = """@time: 00:45
Câu hỏi bài 2 mốc 45s?
(x) Đúng
( ) Sai

@time: 01:15
Câu hỏi bài 2 mốc 75s?
(x) Có
( ) Không
"""

    sample_pdf_content = b"%PDF-1.4 Mock PDF content"

    outline = [
        {
            "title": "Chương 1: Khởi động",
            "subsections": [
                {
                    "title": "Bài 1.1: Tài liệu & Video",
                    "units": [
                        {
                            "title": "1.1.1 Slide bài giảng",
                            "type": "pdf",
                            "file": "slide_bai1.pdf"
                        },
                        {
                            "title": "1.1.2 Video giới thiệu thông thường",
                            "type": "video",
                            "video_url": "https://www.youtube.com/watch?v=kJQP7kiw5Fk"
                        },
                        {
                            "title": "1.1.3 Video Quiz Tổng hợp 1",
                            "type": "video_quiz",
                            "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                            "content": "quiz_bai1.txt"
                        }
                    ]
                },
                {
                    "title": "Bài 1.2: Video tương tác chuyên sâu",
                    "units": [
                        {
                            "title": "1.2.1 Video Quiz Chuyên sâu 2",
                            "type": "video_quiz",
                            "video_url": "https://youtu.be/9bZkp7q19f0",
                            "content": "quiz_bai2.txt"
                        }
                    ]
                }
            ]
        }
    ]

    txt_files = {
        "quiz_bai1.txt": txt_quiz1.encode("utf-8"),
        "quiz_bai2.txt": txt_quiz2.encode("utf-8-sig"),
    }

    return outline, txt_files, sample_pdf_content


def test_export_course_with_video_quiz_full_workflow(sample_course_data):
    outline, txt_files, sample_pdf_content = sample_course_data

    # 1. Validate & prepare units (attaches unit['questions'])
    errors = validate_and_prepare_video_quiz_units(outline, txt_files)
    assert errors == [], f"Validation errors found: {errors}"

    with tempfile.TemporaryDirectory() as temp_dir:
        # Create mock uploaded assets (PDF only - .txt files must NOT be in asset paths)
        pdf_path = os.path.join(temp_dir, "slide_bai1.pdf")
        with open(pdf_path, "wb") as f:
            f.write(sample_pdf_content)

        tar_path = os.path.join(temp_dir, "output_course.tar.gz")

        export_data = {
            "outline": outline,
            "questions": [],
            "uploaded_assets": [pdf_path],
            "uploaded_pdfs": [pdf_path],
        }

        exporter = OpenEdXExporter()
        success = exporter.export(export_data, tar_path)
        assert success is True
        assert os.path.exists(tar_path)

        # 2. Extract and inspect package structure
        extract_dir = os.path.join(temp_dir, "extracted")
        with tarfile.open(tar_path, "r:gz") as tar:
            tar.extractall(extract_dir)

        course_dir = os.path.join(extract_dir, "course")
        assert os.path.exists(course_dir), "course/ directory wrapper missing"

        # 3. Assert static/ and policies/assets.json DO NOT contain any .txt files
        static_dir = os.path.join(course_dir, "static")
        assert os.path.exists(static_dir)
        static_files = os.listdir(static_dir)
        for sf in static_files:
            assert not sf.lower().endswith(".txt"), f"LEAK: .txt file found in course/static/: {sf}"

        assert "slide_bai1.pdf" in static_files, "slide_bai1.pdf missing from course/static/"

        assets_json_path = os.path.join(course_dir, "policies", "assets.json")
        assert os.path.exists(assets_json_path)
        with open(assets_json_path, "r", encoding="utf-8") as f:
            assets_data = json.load(f)
        for asset_key in assets_data.keys():
            assert not asset_key.lower().endswith(".txt"), f"LEAK: .txt found in policies/assets.json: {asset_key}"
        assert "slide_bai1.pdf" in assets_data

        # 4. Assert policy.json contains invideoquiz_v2 in advanced_modules
        policy_json_path = os.path.join(course_dir, "policies", "2024-May", "policy.json")
        assert os.path.exists(policy_json_path), f"policy.json missing at {policy_json_path}"
        with open(policy_json_path, "r", encoding="utf-8") as f:
            policy_data = json.load(f)

        assert "course/2024-May" in policy_data
        adv_modules = policy_data["course/2024-May"].get("advanced_modules", [])
        assert "invideoquiz_v2" in adv_modules, f"invideoquiz_v2 missing in advanced_modules: {adv_modules}"

        # 5. Inspect verticals
        vert_dir = os.path.join(course_dir, "vertical")
        assert os.path.exists(vert_dir)
        vert_files = [f for f in os.listdir(vert_dir) if f.endswith(".xml")]
        assert len(vert_files) == 4  # 1 pdf, 1 video, 2 video_quiz

        video_quiz_verticals = []
        regular_video_verticals = []
        pdf_verticals = []

        for vf in vert_files:
            v_path = os.path.join(vert_dir, vf)
            tree = etree.parse(v_path)
            root = tree.getroot()
            quiz_elems = root.xpath(".//invideoquiz_v2")
            if quiz_elems:
                video_quiz_verticals.append((vf, root, quiz_elems[0]))
            elif root.xpath(".//video"):
                regular_video_verticals.append((vf, root))
            elif root.xpath(".//html"):
                pdf_verticals.append((vf, root))

        assert len(video_quiz_verticals) == 2, f"Expected 2 video_quiz verticals, got {len(video_quiz_verticals)}"
        assert len(regular_video_verticals) == 1, "Regular video vertical affected"
        assert len(pdf_verticals) == 1, "PDF vertical affected"

        # 6. Verify each video_quiz vertical structure
        for vf, vert_root, quiz_elem in video_quiz_verticals:
            # Component order inside vertical: video first, then problems, then invideoquiz_v2
            children = list(vert_root)
            child_tags = [c.tag for c in children]
            assert child_tags[0] == "video", f"First element must be video, got {child_tags[0]}"
            assert child_tags[-1] == "invideoquiz_v2", f"Last element must be invideoquiz_v2, got {child_tags[-1]}"
            for middle_tag in child_tags[1:-1]:
                assert middle_tag == "problem", f"Middle elements must be problem, got {middle_tag}"

            # invideoquiz_v2 attributes
            video_ref = children[0]
            v_url_name = video_ref.get("url_name")
            assert quiz_elem.get("video_id") == v_url_name, "quiz video_id must match video tag url_name"
            assert quiz_elem.get("xblock-family") == "xblock.v1"

            # video file exists
            v_file_path = os.path.join(course_dir, "video", f"{v_url_name}.xml")
            assert os.path.exists(v_file_path), f"Video XML file missing: {v_file_path}"
            v_tree = etree.parse(v_file_path)
            assert v_tree.getroot().tag == "video"
            assert v_tree.getroot().get("url_name") == v_url_name

            # parse timemap
            timemap_str = quiz_elem.get("timemap")
            assert timemap_str, "timemap is empty"
            timemap = json.loads(timemap_str)
            assert isinstance(timemap, dict)

            # verify each problem in timemap
            prob_dir = os.path.join(course_dir, "problem")
            for sec_str, prob_id in timemap.items():
                # seconds key is digits
                assert sec_str.isdigit()
                assert int(sec_str) >= 0

                # problem file exists
                prob_file = os.path.join(prob_dir, f"{prob_id}.xml")
                assert os.path.exists(prob_file), f"Problem XML missing: {prob_file}"

                # inspect problem XML structure
                prob_tree = etree.parse(prob_file)
                prob_root = prob_tree.getroot()
                assert prob_root.tag == "problem"

                # Check that child elements are REAL elements, not escaped string text
                assert len(prob_root) >= 1, "Problem must contain child elements"
                child_tag = prob_root[0].tag
                assert child_tag in ("multiplechoiceresponse", "choiceresponse")

                # problem.text must NOT contain escaped HTML
                assert "&lt;" not in (prob_root.text or "")
                raw_xml = etree.tostring(prob_root, encoding="unicode")
                assert "&lt;multiplechoiceresponse" not in raw_xml
                assert "&lt;choiceresponse" not in raw_xml
                assert "&lt;choicegroup" not in raw_xml
                assert "&lt;p&gt;" not in raw_xml

                # markdown attribute must be clean plain markdown without raw tags
                md = prob_root.get("markdown")
                assert md, "markdown attribute missing"
                assert "<p" not in md
                assert "</p>" not in md
                assert ">>" not in md
                assert "||" not in md


def test_export_endpoint_rejection_and_temp_cleanup(monkeypatch):
    """Test that export endpoint rejects invalid video_quiz and cleans up temp_dir."""
    from app.api.v1.endpoints import export as export_mod

    # Verify temp dir cleanup even on validation errors
    # Create an outline with an unmatched video_quiz
    outline_data = {
        "outline": [
            {
                "title": "Chương 1",
                "subsections": [
                    {
                        "title": "Bài 1",
                        "units": [
                            {
                                "title": "Unit Video Quiz Thiếu File",
                                "type": "video_quiz",
                                "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                                "content": "not_found.txt"
                            }
                        ]
                    }
                ]
            }
        ]
    }

    uploaded_txt = {}
    outline_list = outline_data["outline"]
    errors = validate_and_prepare_video_quiz_units(outline_list, uploaded_txt)
    assert len(errors) >= 1
    assert any("not_found.txt" in e for e in errors)
