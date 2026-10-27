"""
Tests for Course Outline Excel Template generation and error handling.
"""
import sys
from io import BytesIO
from pathlib import Path
import pytest
from openpyxl import load_workbook
from fastapi import UploadFile

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.api.v1.endpoints.outline import (
    REQUIRED_HEADERS,
    OPTIONAL_HEADERS,
    TEMPLATE_HEADERS,
    SUPPORTED_UNIT_TYPES,
    download_outline_template,
    import_outline_excel,
)
from app.config.settings import get_settings


# ===========================================================================
# Task 1 Tests: Template Structure and Clean Import
# ===========================================================================

@pytest.mark.anyio
async def test_download_outline_template_structure():
    """Endpoint download_outline_template phải sinh file .xlsx với đúng cấu trúc:
    - 2 sheets: 'Mẫu' và 'Hướng dẫn'.
    - Sheet 'Mẫu': Header khớp TEMPLATE_HEADERS, đủ 1 dòng cho mỗi SUPPORTED_UNIT_TYPES,
      và 1 dòng để trống Type nhưng điền Slide để kiểm tra tự nhận diện.
    - Sheet 'Hướng dẫn': Mô tả các cột, danh sách Type hợp lệ, quy tắc đặt tên,
      giới hạn kích thước lấy từ settings.file.max_file_size (50MB).
    """
    resp = await download_outline_template()
    assert resp.status_code == 200
    assert resp.media_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert 'filename="outline_template.xlsx"' in resp.headers.get("Content-Disposition", "")

    # Đọc lại bằng openpyxl
    wb = load_workbook(BytesIO(resp.body))
    assert wb.sheetnames == ["Mẫu", "Hướng dẫn"]

    # 1. Kiểm tra sheet 'Mẫu'
    ws_mau = wb["Mẫu"]
    headers = [cell.value for cell in ws_mau[1] if cell.value is not None]
    assert headers == TEMPLATE_HEADERS
    assert headers == ["Chapter", "Lesson", "Unit", "Type", "Content", "Slide", "Youtube"]

    rows = list(ws_mau.iter_rows(min_row=2, values_only=True))
    # Phải có ít nhất len(SUPPORTED_UNIT_TYPES) + 1 dòng (cho auto-detect)
    assert len(rows) >= len(SUPPORTED_UNIT_TYPES) + 1

    # Kiểm tra sự xuất hiện của các types được hỗ trợ
    types_in_sample = [r[headers.index("Type")] for r in rows if r[headers.index("Type")]]
    for expected_type in SUPPORTED_UNIT_TYPES:
        assert expected_type in types_in_sample, f"Thiếu ví dụ cho Type '{expected_type}' trong sheet Mẫu"

    # Kiểm tra có 1 dòng không điền Type nhưng có điền Slide hoặc Youtube (auto-detection)
    auto_detect_rows = [r for r in rows if not r[headers.index("Type")] and (r[headers.index("Slide")] or r[headers.index("Youtube")])]
    assert len(auto_detect_rows) >= 1, "Cần có ít nhất 1 dòng để trống Type nhưng có Slide/Youtube để minh họa tự nhận diện"

    # 2. Kiểm tra sheet 'Hướng dẫn'
    ws_guide = wb["Hướng dẫn"]
    guide_text = "\n".join(" ".join(str(c) for c in row if c is not None) for row in ws_guide.iter_rows(values_only=True))

    # Cột bắt buộc & tùy chọn
    for h in REQUIRED_HEADERS:
        assert h in guide_text
    for h in OPTIONAL_HEADERS:
        assert h in guide_text

    # Danh sách Type hợp lệ
    for expected_type in SUPPORTED_UNIT_TYPES:
        assert expected_type in guide_text

    # Quy tắc đặt tên file (docs 3.4.2: không dấu, không khoảng trắng)
    assert "dấu" in guide_text.lower() or "khoảng trắng" in guide_text.lower() or "ký tự" in guide_text.lower()

    # Giới hạn dung lượng từ cấu hình settings
    settings = get_settings()
    max_mb = settings.file.max_file_size // (1024 * 1024)
    assert f"{max_mb}MB" in guide_text or f"{max_mb} MB" in guide_text or str(settings.file.max_file_size) in guide_text

    # Ghi chú tương thích ngược 5 cột
    assert "5 cột" in guide_text or "tương thích" in guide_text.lower()


@pytest.mark.anyio
async def test_template_file_imports_cleanly():
    """Đưa chính file template sinh ra vào import_outline_excel():
    - Phải thành công (success=True).
    - warnings phải rỗng (không thiếu Lesson, không có cảnh báo).
    - Các unit nhận đúng type mong đợi.
    """
    resp = await download_outline_template()
    upload = UploadFile(filename="outline_template.xlsx", file=BytesIO(resp.body))

    res = await import_outline_excel(upload)
    assert res.success is True, f"Import thất bại: {res.message}"
    assert len(res.warnings) == 0, f"Có cảnh báo không mong muốn: {res.warnings}"

    outline = res.outline.get("outline", [])
    assert len(outline) > 0

    # Gom tất cả các unit từ mọi chapter và subsection
    all_units = []
    for chapter in outline:
        for sub in chapter.get("subsections", []):
            for unit in sub.get("units", []):
                all_units.append(unit)

    # Đảm bảo mỗi unit tương ứng với từng SUPPORTED_UNIT_TYPES đều được tạo ra đúng type
    unit_types = {u.get("type") for u in all_units}
    for expected_type in SUPPORTED_UNIT_TYPES:
        assert expected_type in unit_types, f"Unit type '{expected_type}' không được tạo đúng sau khi import"
