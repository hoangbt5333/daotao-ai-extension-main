"""
Tests for Video Quiz question parser and validator (TDD).
Covers:
- UTF-8 with BOM / UTF-8 decoding and error handling
- Line number accuracy preserving blank lines
- Two consecutive @time: directives
- @time: at EOF with no question
- Missing @time: on a question
- Duplicate timestamps (e.g. 01:30 vs 90s)
- Invalid timestamp formats
- Mixing ( ) and [ ] choices in a single question
- Invalid questions (<2 choices, radio with 0 or >1 correct, checkbox with 0 correct)
- All errors collected in a single batch list
"""
import sys
from pathlib import Path
import pytest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.services.export.video_quiz_helper import parse_video_quiz_text


def test_parse_valid_mixed_quiz():
    text = """@tag: chuong1, video1

@time: 01:30
Câu 1: Câu hỏi một đáp án đúng
(!) Lựa chọn 1 (shuffle)
(x) Lựa chọn 2 đúng
( ) Lựa chọn 3 sai
(@) Lựa chọn 4 cố định

@time: 02:45
Câu 2: Câu hỏi nhiều đáp án đúng
[x] Đáp án A
[ ] Đáp án B
[x] Đáp án C

@time: 03:15
Câu 3: Câu hỏi radio thứ hai
(x) Đúng
( ) Sai
"""
    questions, errors = parse_video_quiz_text(text, filename="bai1.txt")
    assert errors == []
    assert len(questions) == 3

    # Q1: multiple_choice
    q1 = questions[0]
    assert q1["type"] == "multiple_choice"
    assert q1["timestamp"] == "01:30"
    assert q1["seconds"] == 90
    assert q1["line"] == 4
    assert len(q1["choices"]) == 4
    assert q1["correct_answers"] == [1]
    assert q1["tags"] == ["chuong1", "video1"]

    # Q2: multiple_select
    q2 = questions[1]
    assert q2["type"] == "multiple_select"
    assert q2["timestamp"] == "02:45"
    assert q2["seconds"] == 165
    assert q2["line"] == 11
    assert len(q2["choices"]) == 3
    assert q2["correct_answers"] == [0, 2]
    assert q2["tags"] == ["chuong1", "video1"]  # tags persist

    # Q3: multiple_choice
    q3 = questions[2]
    assert q3["type"] == "multiple_choice"
    assert q3["timestamp"] == "03:15"
    assert q3["seconds"] == 195
    assert q3["correct_answers"] == [0]


def test_parse_utf8_sig_and_invalid_encoding():
    # Valid utf-8-sig bytes
    valid_bytes = "@time: 00:10\nCâu hỏi?\n(x) A\n( ) B\n".encode("utf-8-sig")
    questions, errors = parse_video_quiz_text(valid_bytes, filename="quiz.txt")
    assert errors == []
    assert len(questions) == 1

    # Invalid utf-8 bytes (raw latin-1 or invalid sequence)
    invalid_bytes = b"\xff\xfe\x00\x00Invalid UTF8"
    questions, errors = parse_video_quiz_text(invalid_bytes, filename="broken.txt")
    assert len(errors) == 1
    assert "broken.txt" in errors[0]
    assert "file phải lưu dạng utf-8" in errors[0].lower()


def test_line_number_accuracy_with_blank_lines():
    text = """


@time: 00:30

Câu hỏi ở dòng 6?

(x) Đúng

( ) Sai
"""
    questions, errors = parse_video_quiz_text(text, filename="lines.txt")
    assert errors == []
    assert len(questions) == 1
    assert questions[0]["line"] == 6


def test_consecutive_time_directives():
    text = """@time: 00:30
@time: 00:45
Câu hỏi?
(x) A
( ) B
"""
    questions, errors = parse_video_quiz_text(text, filename="consec.txt")
    assert any("hai chỉ thị @time: liên tiếp" in e for e in errors)
    assert any("Dòng 2" in e for e in errors)


def test_time_directive_at_eof():
    text = """@time: 00:30
Câu hỏi 1?
(x) A
( ) B

@time: 01:00
"""
    questions, errors = parse_video_quiz_text(text, filename="eof.txt")
    assert any("không có câu hỏi theo sau" in e for e in errors)
    assert any("Dòng 6" in e for e in errors)


def test_missing_time_directive():
    text = """@time: 00:30
Câu hỏi 1?
(x) A
( ) B

Câu hỏi 2 không có time?
(x) A
( ) B
"""
    questions, errors = parse_video_quiz_text(text, filename="missing_time.txt")
    assert any("thiếu mốc thời gian @time:" in e for e in errors)
    assert any("Dòng 6" in e for e in errors)


def test_duplicate_timestamps():
    text = """@time: 01:30
Câu 1?
(x) A
( ) B

@time: 90
Câu 2 trùng mốc 90s?
(x) C
( ) D
"""
    questions, errors = parse_video_quiz_text(text, filename="dup.txt")
    assert any("trùng với mốc '01:30'" in e or "bị trùng" in e for e in errors)
    assert any("Dòng 6" in e for e in errors)


def test_invalid_and_negative_timestamps():
    text = """@time: abc
Câu 1?
(x) A
( ) B

@time: -15
Câu 2?
(x) C
( ) D
"""
    questions, errors = parse_video_quiz_text(text, filename="invalid_ts.txt")
    assert any("Mốc thời gian 'abc' không hợp lệ" in e for e in errors)
    assert any("không được âm" in e or "không hợp lệ" in e for e in errors)


def test_mixing_radio_and_checkbox_in_same_question():
    text = """@time: 00:40
Câu hỏi bị trộn lẫn marker?
(x) Đáp án radio 1
( ) Đáp án radio 2
[x] Đáp án checkbox lẫn vào
"""
    questions, errors = parse_video_quiz_text(text, filename="mixed.txt")
    assert any("Không được trộn lẫn" in e for e in errors)
    assert any("Dòng 5" in e for e in errors)


def test_invalid_choices_validation():
    text = """@time: 00:10
Câu chỉ có 1 lựa chọn?
(x) Duy nhất

@time: 00:20
Câu radio không có đáp án đúng?
( ) A
( ) B

@time: 00:30
Câu radio có 2 đáp án đúng?
(x) A
(x) B

@time: 00:40
Câu checkbox không có đáp án đúng?
[ ] A
[ ] B
"""
    questions, errors = parse_video_quiz_text(text, filename="invalid_q.txt")
    assert any("ít nhất 2 đáp án lựa chọn" in e for e in errors)
    assert any("phải có 1 đáp án đúng" in e for e in errors)
    assert any("nhiều hơn 1 đáp án đúng" in e for e in errors)
    assert any("ít nhất 1 đáp án đúng" in e for e in errors)


def test_batch_all_errors_collected():
    text = """@time: 00:10
@time: 00:20
Câu 1 thiếu đáp án đúng?
( ) A
( ) B

Câu 2 thiếu time?
[ ] C
[ ] D
"""
    questions, errors = parse_video_quiz_text(text, filename="batch_err.txt")
    # Must report consecutive time, no correct answer for Q1, missing time for Q2, no correct answer for Q2
    assert len(errors) >= 4


from app.services.export.video_quiz_helper import validate_and_prepare_video_quiz_units


def test_validate_and_prepare_video_quiz_units_success():
    outline = [
        {
            "title": "Chương 1",
            "subsections": [
                {
                    "title": "Bài 1",
                    "units": [
                        {
                            "title": "Unit Video Quiz 1",
                            "type": "video_quiz",
                            "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                            "content": "quiz1.txt"
                        }
                    ]
                }
            ]
        }
    ]
    txt_files = {
        "quiz1.txt": b"@time: 01:00\nCau hoi?\n(x) A\n( ) B\n"
    }
    errors = validate_and_prepare_video_quiz_units(outline, txt_files)
    assert errors == []
    u = outline[0]["subsections"][0]["units"][0]
    assert "questions" in u
    assert len(u["questions"]) == 1
    assert u["questions"][0]["type"] == "multiple_choice"


def test_validate_and_prepare_video_quiz_units_errors():
    outline = [
        {
            "title": "Chương 1",
            "subsections": [
                {
                    "title": "Bài 1",
                    "units": [
                        {
                            "title": "Unit Lỗi 1",
                            "type": "video_quiz",
                            "video_url": "<iframe src='https://www.youtube.com/embed/123'></iframe>",
                            "content": "missing.txt"
                        },
                        {
                            "title": "Unit Lỗi 2",
                            "type": "video_quiz",
                            "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                            "content": ""
                        }
                    ]
                }
            ]
        }
    ]
    txt_files = {
        "orphan.txt": b"@time: 01:00\nCau hoi?\n(x) A\n( ) B\n"
    }
    errors = validate_and_prepare_video_quiz_units(outline, txt_files)
    assert any("không phải là YouTube hợp lệ" in e for e in errors)
    assert any("Không tìm thấy file câu hỏi 'missing.txt'" in e for e in errors)
    assert any("Chưa khai báo tên file câu hỏi" in e for e in errors)
    assert any("File 'orphan.txt': File câu hỏi đã tải lên nhưng không khớp" in e for e in errors)
