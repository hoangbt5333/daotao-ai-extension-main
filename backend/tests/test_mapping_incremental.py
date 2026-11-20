"""
Tests for incremental PDF mapping endpoint (/api/v1/mapping/pdfs).

Requirements:
- Incremental mode only maps to units WITHOUT any file.
- Never changes type or fields of units that already have a file or have protected types (video_quiz, audio, embed).
- Never creates new units.
- Never uses add_file_to_first_available_unit fallback.
- Returns list of unmatched files in `unmatched_files`.
- Preserves full backward compatibility when incremental=False.
"""
import copy
import json
import sys
from pathlib import Path
import pytest

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_incremental_mapping_preserves_manual_and_filled_units():
    """
    Test incremental mode:
    - Outline has a manually edited unit (type: video_quiz) and a unit already having a file.
    - An empty unit is also present.
    - Two files are sent: one matches the empty unit, one does not match anything.
    - Result:
      * Only the empty unit receives the file.
      * All other units preserve every single field.
      * No new units are created.
      * The unmatched file is returned in unmatched_files.
    """
    original_outline = {
        "outline": [
            {
                "title": "Chương 1: Mở đầu",
                "subsections": [
                    {
                        "title": "Bài 1: Giới thiệu",
                        "units": [
                            {
                                "title": "Kiểm tra tương tác",
                                "type": "video_quiz",
                                "quiz_file": "quiz_intro.txt",
                                "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                                "content": "quiz_intro.txt",
                                "user_notes": "Chỉnh sửa thủ công bởi giảng viên"
                            },
                            {
                                "title": "Slide lý thuyết đã gán",
                                "type": "pdf",
                                "file": "slide_ly_thuyet_cu.pdf",
                                "custom_field": "preserve_this_value"
                            },
                            {
                                "title": "Bài tập tự luyện",
                                "type": "text",
                                "content": ""
                            }
                        ]
                    }
                ]
            }
        ]
    }

    outline_snapshot = copy.deepcopy(original_outline)

    # 2 files: one matching "Bài tập tự luyện", one completely unmatched
    files_payload = [
        ("files", ("Bài tập tự luyện.pdf", b"%PDF-1.4 mock content 1", "application/pdf")),
        ("files", ("hoan_toan_khong_khop_unit_nao.pdf", b"%PDF-1.4 mock content 2", "application/pdf"))
    ]

    response = client.post(
        "/api/v1/mapping/pdfs",
        data={
            "outline": json.dumps(original_outline),
            "incremental": "true"
        },
        files=files_payload
    )

    assert response.status_code == 200, f"Expected 200 but got {response.status_code}: {response.text}"
    data = response.json()

    assert data["success"] is True
    assert data["mapped_count"] == 1
    assert data["unmatched_files"] == ["hoan_toan_khong_khop_unit_nao.pdf"]

    mapped_outline = data["mapped_outline"]
    mapped_units = mapped_outline["outline"][0]["subsections"][0]["units"]

    # 1. No new units created: still exactly 3 units
    assert len(mapped_units) == 3, f"Expected exactly 3 units, got {len(mapped_units)}"

    # 2. Unit 0 (video_quiz) retains every single field unchanged
    expected_unit_0 = outline_snapshot["outline"][0]["subsections"][0]["units"][0]
    assert mapped_units[0] == expected_unit_0, f"Unit 0 modified! Got {mapped_units[0]}"

    # 3. Unit 1 (existing file) retains every single field unchanged
    expected_unit_1 = outline_snapshot["outline"][0]["subsections"][0]["units"][1]
    assert mapped_units[1] == expected_unit_1, f"Unit 1 modified! Got {mapped_units[1]}"

    # 4. Unit 2 (empty unit) received the matched file
    assert mapped_units[2]["title"] == "Bài tập tự luyện"
    assert mapped_units[2]["type"] == "pdf"
    assert mapped_units[2]["file"] == "Bài tập tự luyện.pdf"


def test_incremental_mapping_all_unmatched_does_not_modify_outline():
    """
    When all incoming files in incremental mode are unmatched:
    - Outline remains 100% unchanged.
    - No units created.
    - mapped_count = 0.
    - All files in unmatched_files.
    """
    outline = {
        "outline": [
            {
                "title": "Chương 2",
                "subsections": [
                    {
                        "title": "Bài 2",
                        "units": [
                            {
                                "title": "Bài giảng Audio",
                                "type": "audio",
                                "audio_file": "bai2.mp3"
                            }
                        ]
                    }
                ]
            }
        ]
    }
    outline_snapshot = copy.deepcopy(outline)

    files_payload = [
        ("files", ("unrelated_1.pdf", b"%PDF-1.4 mock", "application/pdf")),
        ("files", ("unrelated_2.pdf", b"%PDF-1.4 mock", "application/pdf"))
    ]

    response = client.post(
        "/api/v1/mapping/pdfs",
        data={
            "outline": json.dumps(outline),
            "incremental": "true"
        },
        files=files_payload
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["mapped_count"] == 0
    assert set(data["unmatched_files"]) == {"unrelated_1.pdf", "unrelated_2.pdf"}
    assert data["mapped_outline"] == outline_snapshot


def test_backward_compatibility_non_incremental_mode():
    """
    When incremental=False:
    - Preserves standard behavior of full mapping.
    - mapped_count equals total files.
    - unmatched_files is empty.
    """
    outline = {
        "outline": [
            {
                "title": "Chương 1",
                "subsections": [
                    {
                        "title": "Bài 1",
                        "units": [
                            {
                                "title": "Slide bài 1",
                                "type": "text"
                            }
                        ]
                    }
                ]
            }
        ]
    }

    files_payload = [
        ("files", ("Slide bài 1.pdf", b"%PDF-1.4 mock", "application/pdf")),
    ]

    response = client.post(
        "/api/v1/mapping/pdfs",
        data={
            "outline": json.dumps(outline),
            "incremental": "false"
        },
        files=files_payload
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["mapped_count"] == 1
    assert data["unmatched_files"] == []
    assert data["mapped_outline"]["outline"][0]["subsections"][0]["units"][0]["file"] == "Slide bài 1.pdf"
