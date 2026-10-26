"""
Task 1: Tests for HTML component file structure in OpenEdX export.

Kiểm tra rằng output tar.gz khớp đúng chuẩn Studio OLX:
- vertical/{id}.xml: thẻ <vertical> KHÔNG có url_name, các thẻ con chỉ có url_name.
- html/{uuid}.xml: descriptor tồn tại, có thuộc tính filename.
- html/{uuid}.html: file nội dung tồn tại và không rỗng.
- policies/assets.json: sinh dict-map đúng chuẩn (không phải {"assets": []}).
"""
import sys
import tarfile
import tempfile
import json
import pytest
import xml.etree.ElementTree as ET
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

# Import trực tiếp module, tránh import chain qua app.services.__init__
# (chain đó kéo theo LLM providers cần 'requests' và env vars không cần thiết ở đây)
import importlib
_mod = importlib.import_module("app.services.export.openedx")
OpenEdXExporter = _mod.OpenEdXExporter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _export_to_tmpfile(outline_data: list, pdf_paths: list = None) -> Path:
    """Run the exporter and return path to the resulting tar.gz."""
    exporter = OpenEdXExporter()
    data = {
        "outline": outline_data,
        "questions": [],
        "uploaded_pdfs": pdf_paths or [],
    }
    out = Path(tempfile.mktemp(suffix=".tar.gz"))
    ok = exporter.export(data, str(out))
    assert ok, "Exporter returned False — export failed"
    return out


def _members(tar: tarfile.TarFile) -> set:
    return {m.name for m in tar.getmembers()}


def _read(tar: tarfile.TarFile, name: str) -> str:
    return tar.extractfile(name).read().decode("utf-8")


# ---------------------------------------------------------------------------
# Fixtures: minimal outline dicts (không chứa dữ liệu thật)
# ---------------------------------------------------------------------------

OUTLINE_TEXT_UNIT = [
    {
        "title": "Chương 1",
        "subsections": [
            {
                "title": "Bài 1",
                "units": [
                    {"title": "Unit Text", "type": "text", "html_content": "<p>Nội dung văn bản mẫu</p>"},
                ],
            }
        ],
    }
]

OUTLINE_PDF_UNIT = [
    {
        "title": "Chương 1",
        "subsections": [
            {
                "title": "Bài 1",
                "units": [
                    {"title": "Unit PDF", "type": "pdf", "file": "sample.pdf"},
                ],
            }
        ],
    }
]

OUTLINE_VIDEO_PDF = [
    {
        "title": "Chương 1",
        "subsections": [
            {
                "title": "Bài 1",
                "units": [
                    {
                        "title": "Unit Video+PDF",
                        "type": "video_pdf",
                        "video_url": "https://www.youtube.com/watch?v=Z0yt68n_Qhw",
                        "pdf_file": "sample.pdf",
                    },
                ],
            }
        ],
    }
]

OUTLINE_MIXED = [
    {
        "title": "Chương 1",
        "subsections": [
            {
                "title": "Bài 1",
                "units": [
                    {"title": "Unit PDF", "type": "pdf", "file": "slide.pdf"},
                    {"title": "Unit Text", "type": "text", "html_content": "<p>Text</p>"},
                ],
            },
            {
                "title": "Bài 2",
                "units": [
                    {"title": "Unit Video", "type": "video", "video_url": "https://youtu.be/Z0yt68n_Qhw"},
                ],
            },
        ],
    }
]


# ===========================================================================
# T1-1: vertical XML không có url_name trên thẻ <vertical>
# ===========================================================================

def test_vertical_no_url_name_attribute():
    """<vertical> chỉ được mang display_name, không được mang url_name."""
    out = _export_to_tmpfile(OUTLINE_TEXT_UNIT)
    with tarfile.open(out) as tar:
        vertical_files = [m.name for m in tar.getmembers()
                          if m.name.startswith("course/vertical/") and m.name.endswith(".xml")]
        assert vertical_files, "Không tìm thấy file nào trong course/vertical/"
        for vf in vertical_files:
            xml_str = _read(tar, vf)
            root = ET.fromstring(xml_str)
            assert root.tag == "vertical"
            assert "display_name" in root.attrib, f"{vf}: thiếu display_name"
            assert "url_name" not in root.attrib, (
                f"{vf}: <vertical> không được có url_name, nhưng tìm thấy: {root.attrib}"
            )


# ===========================================================================
# T1-2: thẻ con <html> trong vertical chỉ có url_name, không có display_name
# ===========================================================================

def test_html_child_in_vertical_has_only_url_name():
    """Thẻ <html> bên trong vertical là stub tham chiếu: chỉ có url_name."""
    out = _export_to_tmpfile(OUTLINE_TEXT_UNIT)
    with tarfile.open(out) as tar:
        vertical_files = [m.name for m in tar.getmembers()
                          if m.name.startswith("course/vertical/") and m.name.endswith(".xml")]
        for vf in vertical_files:
            xml_str = _read(tar, vf)
            root = ET.fromstring(xml_str)
            for child in root:
                if child.tag == "html":
                    assert "url_name" in child.attrib, f"{vf}: <html> thiếu url_name"
                    assert "display_name" not in child.attrib, (
                        f"{vf}: <html> không được có display_name trong vertical stub, "
                        f"nhưng tìm thấy: {child.attrib}"
                    )


# ===========================================================================
# T1-3: file html/{uuid}.xml tồn tại và có thuộc tính filename
# ===========================================================================

def test_html_descriptor_xml_exists_with_filename():
    """Mỗi html component phải có file descriptor course/html/{uuid}.xml với thuộc tính filename."""
    out = _export_to_tmpfile(OUTLINE_PDF_UNIT)
    with tarfile.open(out) as tar:
        members = _members(tar)

        # Tìm tất cả uuid từ thẻ <html> trong các vertical
        html_uuids = []
        for m in tar.getmembers():
            if m.name.startswith("course/vertical/") and m.name.endswith(".xml"):
                root = ET.fromstring(_read(tar, m.name))
                for child in root:
                    if child.tag == "html":
                        html_uuids.append(child.attrib["url_name"])

        assert html_uuids, "Không tìm thấy thẻ <html> nào trong các vertical"

        for uuid in html_uuids:
            desc_path = f"course/html/{uuid}.xml"
            assert desc_path in members, f"Descriptor {desc_path} không tồn tại trong tar.gz"

            # Đọc và kiểm tra thuộc tính filename
            root = ET.fromstring(_read(tar, desc_path))
            assert root.tag == "html"
            assert "filename" in root.attrib, f"{desc_path}: thiếu thuộc tính filename"
            assert root.attrib["filename"] == uuid, (
                f"{desc_path}: filename='{root.attrib['filename']}' khác uuid '{uuid}'"
            )


# ===========================================================================
# T1-4: file html/{uuid}.html tồn tại và không rỗng
# ===========================================================================

def test_html_content_file_exists_and_nonempty():
    """Mỗi html component phải có file nội dung course/html/{uuid}.html, không được rỗng."""
    out = _export_to_tmpfile(OUTLINE_PDF_UNIT)
    with tarfile.open(out) as tar:
        members = _members(tar)

        html_uuids = []
        for m in tar.getmembers():
            if m.name.startswith("course/vertical/") and m.name.endswith(".xml"):
                root = ET.fromstring(_read(tar, m.name))
                for child in root:
                    if child.tag == "html":
                        html_uuids.append(child.attrib["url_name"])

        for uuid in html_uuids:
            content_path = f"course/html/{uuid}.html"
            assert content_path in members, f"Content file {content_path} không tồn tại trong tar.gz"
            content = _read(tar, content_path)
            assert content.strip(), f"{content_path}: file nội dung HTML bị rỗng"


# ===========================================================================
# T1-5: type 'pdf' sinh iframe đúng trong file .html
# ===========================================================================

def test_pdf_unit_iframe_in_html_file():
    """Unit type='pdf' phải sinh thẻ <iframe src='/static/...'> trong file .html riêng."""
    out = _export_to_tmpfile(OUTLINE_PDF_UNIT)
    with tarfile.open(out) as tar:
        html_uuids = []
        for m in tar.getmembers():
            if m.name.startswith("course/vertical/") and m.name.endswith(".xml"):
                root = ET.fromstring(_read(tar, m.name))
                for child in root:
                    if child.tag == "html":
                        html_uuids.append(child.attrib["url_name"])

        found_iframe = False
        for uuid in html_uuids:
            content = _read(tar, f"course/html/{uuid}.html")
            if "/static/sample.pdf" in content and "iframe" in content:
                found_iframe = True
        assert found_iframe, "Không tìm thấy iframe src='/static/sample.pdf' trong bất kỳ file html nào"


# ===========================================================================
# T1-6: type 'text' sinh nội dung html_content trong file .html
# ===========================================================================

def test_text_unit_html_content_in_file():
    """Unit type='text' với html_content phải ghi nội dung vào file .html riêng."""
    out = _export_to_tmpfile(OUTLINE_TEXT_UNIT)
    with tarfile.open(out) as tar:
        html_uuids = []
        for m in tar.getmembers():
            if m.name.startswith("course/vertical/") and m.name.endswith(".xml"):
                root = ET.fromstring(_read(tar, m.name))
                for child in root:
                    if child.tag == "html":
                        html_uuids.append(child.attrib["url_name"])

        found = False
        for uuid in html_uuids:
            content = _read(tar, f"course/html/{uuid}.html")
            if "Nội dung văn bản mẫu" in content:
                found = True
        assert found, "Nội dung html_content không được ghi vào file .html"


# ===========================================================================
# T1-7: raw-HTML types (pdf, docx) có editor="raw" trong descriptor XML
# ===========================================================================

def test_pdf_descriptor_has_raw_editor():
    """Unit type='pdf' phải có editor='raw' trong file descriptor .xml (khớp chuẩn Studio)."""
    out = _export_to_tmpfile(OUTLINE_PDF_UNIT)
    with tarfile.open(out) as tar:
        html_uuids = []
        for m in tar.getmembers():
            if m.name.startswith("course/vertical/") and m.name.endswith(".xml"):
                root = ET.fromstring(_read(tar, m.name))
                for child in root:
                    if child.tag == "html":
                        html_uuids.append(child.attrib["url_name"])

        for uuid in html_uuids:
            desc_root = ET.fromstring(_read(tar, f"course/html/{uuid}.xml"))
            assert desc_root.get("editor") == "raw", (
                f"course/html/{uuid}.xml: thiếu editor='raw' cho loại PDF"
            )


# ===========================================================================
# T1-8: text unit KHÔNG có editor="raw" trong descriptor XML
# ===========================================================================

def test_text_descriptor_no_raw_editor():
    """Unit type='text' dùng editor mặc định — descriptor .xml không được có editor='raw'."""
    out = _export_to_tmpfile(OUTLINE_TEXT_UNIT)
    with tarfile.open(out) as tar:
        html_uuids = []
        for m in tar.getmembers():
            if m.name.startswith("course/vertical/") and m.name.endswith(".xml"):
                root = ET.fromstring(_read(tar, m.name))
                for child in root:
                    if child.tag == "html":
                        html_uuids.append(child.attrib["url_name"])

        for uuid in html_uuids:
            desc_root = ET.fromstring(_read(tar, f"course/html/{uuid}.xml"))
            assert desc_root.get("editor") != "raw", (
                f"course/html/{uuid}.xml: type='text' không được có editor='raw'"
            )


# ===========================================================================
# T1-9: assets.json sinh dict-map đúng chuẩn Studio (không phải {"assets": []})
# ===========================================================================

def test_assets_json_is_dict_map(tmp_path):
    """policies/assets.json phải là dict map theo tên file, không phải list rỗng."""
    # Tạo một file PDF giả trong tmp_path để có asset thực tế
    fake_pdf = tmp_path / "slide.pdf"
    fake_pdf.write_bytes(b"%PDF-1.4 fake")

    out = _export_to_tmpfile(OUTLINE_PDF_UNIT, pdf_paths=[str(fake_pdf)])
    with tarfile.open(out) as tar:
        assets_raw = _read(tar, "course/policies/assets.json")
        assets = json.loads(assets_raw)

        # Phải là dict, không phải {"assets": []}
        assert isinstance(assets, dict), "assets.json phải là dict map, không phải object có key 'assets'"
        assert "assets" not in assets, (
            "assets.json không được có dạng {\"assets\": [...]} — phải là dict map theo tên file"
        )
        # File slide.pdf đã copy vào static/ => phải có entry
        assert "slide.pdf" in assets, "slide.pdf phải xuất hiện trong assets.json"
        entry = assets["slide.pdf"]
        assert entry["contentType"] == "application/pdf", f"contentType sai: {entry['contentType']}"
        assert "filename" in entry, "Thiếu trường 'filename' trong assets.json entry"


# ===========================================================================
# T1-10: assets.json không có entry khi static/ rỗng
# ===========================================================================

def test_assets_json_empty_when_no_static():
    """Khi không upload file nào, assets.json phải là dict rỗng {}."""
    out = _export_to_tmpfile(OUTLINE_TEXT_UNIT, pdf_paths=[])
    with tarfile.open(out) as tar:
        assets = json.loads(_read(tar, "course/policies/assets.json"))
        assert isinstance(assets, dict)
        assert len(assets) == 0, f"Mong đợi dict rỗng, nhưng có: {list(assets.keys())}"


# ===========================================================================
# T1-11: outline hỗn hợp — mỗi unit có đúng 1 cặp file descriptor + content
# ===========================================================================

def test_mixed_outline_each_unit_has_html_pair():
    """Outline hỗn hợp: mỗi html component sinh đúng 1 cặp .xml + .html."""
    out = _export_to_tmpfile(OUTLINE_MIXED)
    with tarfile.open(out) as tar:
        members = _members(tar)
        html_uuids = []
        for m in tar.getmembers():
            if m.name.startswith("course/vertical/") and m.name.endswith(".xml"):
                root = ET.fromstring(_read(tar, m.name))
                for child in root:
                    if child.tag == "html":
                        html_uuids.append(child.attrib["url_name"])

        # 2 unit có html (PDF + Text), 1 unit là video (không có html)
        assert len(html_uuids) == 2, f"Mong đợi 2 html component, nhưng có {len(html_uuids)}"
        for uuid in html_uuids:
            assert f"course/html/{uuid}.xml" in members
            assert f"course/html/{uuid}.html" in members


# ===========================================================================
# T2: Audio Unit Tests
# ===========================================================================

OUTLINE_AUDIO_UNIT = [
    {
        "title": "Chương 1",
        "subsections": [
            {
                "title": "Bài 1",
                "units": [
                    {
                        "title": "File nghe bài 1",
                        "type": "audio",
                        "file": "audio-test.mp3",
                    },
                ],
            }
        ],
    }
]

def test_audio_unit_vertical_and_html_files():
    """Unit type='audio' phải sinh descriptor Raw HTML và thẻ audio controls trong file .html."""
    out = _export_to_tmpfile(OUTLINE_AUDIO_UNIT)
    with tarfile.open(out) as tar:
        members = _members(tar)
        html_uuids = []
        for m in tar.getmembers():
            if m.name.startswith("course/vertical/") and m.name.endswith(".xml"):
                root = ET.fromstring(_read(tar, m.name))
                for child in root:
                    if child.tag == "html":
                        html_uuids.append(child.attrib["url_name"])

        assert len(html_uuids) == 1, "Phải có đúng 1 html component cho audio unit"
        uuid = html_uuids[0]

        # 1. Descriptor XML phải có editor="raw"
        desc_path = f"course/html/{uuid}.xml"
        assert desc_path in members, f"Thiếu {desc_path}"
        desc_root = ET.fromstring(_read(tar, desc_path))
        assert desc_root.get("editor") == "raw", "Audio descriptor phải có editor='raw'"
        assert desc_root.get("filename") == uuid

        # 2. File .html phải chứa audio tag đúng chuẩn Studio
        content_path = f"course/html/{uuid}.html"
        assert content_path in members, f"Thiếu {content_path}"
        html_content = _read(tar, content_path)
        assert "<audio controls>" in html_content
        assert '<source src="/static/audio-test.mp3" type="audio/mp3">' in html_content
        assert "<p>File nghe bài 1</p>" in html_content


def test_audio_unit_file_copied_to_static_and_assets_json(tmp_path):
    """File MP3 upload phải được copy vào static/ và ghi contentType='audio/mpeg' trong assets.json."""
    fake_mp3 = tmp_path / "audio-test.mp3"
    fake_mp3.write_bytes(b"ID3fake_mp3_content")

    out = _export_to_tmpfile(OUTLINE_AUDIO_UNIT, pdf_paths=[str(fake_mp3)])
    with tarfile.open(out) as tar:
        members = _members(tar)

        # File mp3 phải có trong static/
        assert "course/static/audio-test.mp3" in members, "audio-test.mp3 không được copy vào course/static/"

        # assets.json phải có contentType là audio/mpeg
        assets = json.loads(_read(tar, "course/policies/assets.json"))
        assert "audio-test.mp3" in assets, "audio-test.mp3 thiếu trong assets.json"
        entry = assets["audio-test.mp3"]
        assert entry["contentType"] == "audio/mpeg", f"MIME type sai: {entry['contentType']}"
        assert "filename" in entry
        assert entry["locked"] is False


def test_audio_unit_supports_audio_file_field():
    """Unit type='audio' có thể nhận tên file qua trường 'audio_file' thay vì 'file'."""
    outline = [
        {
            "title": "Chương 1",
            "subsections": [
                {
                    "title": "Bài 1",
                    "units": [
                        {
                            "title": "Nghe hiểu",
                            "type": "audio",
                            "audio_file": "listening-02.mp3",
                        },
                    ],
                }
            ],
        }
    ]
    out = _export_to_tmpfile(outline)
    with tarfile.open(out) as tar:
        found_audio = False
        for m in tar.getmembers():
            if m.name.startswith("course/html/") and m.name.endswith(".html"):
                content = _read(tar, m.name)
                if '<source src="/static/listening-02.mp3" type="audio/mp3">' in content:
                    found_audio = True
                    break
        assert found_audio, "Không tìm thấy listening-02.mp3 trong file html của audio component"


def test_audio_unit_without_file():
    """Unit type='audio' khi không có file thì tạo thông báo phù hợp, không crash."""
    outline = [
        {
            "title": "Chương 1",
            "subsections": [
                {
                    "title": "Bài 1",
                    "units": [
                        {"title": "Unit Audio Trống", "type": "audio"},
                    ],
                }
            ],
        }
    ]
    out = _export_to_tmpfile(outline)
    with tarfile.open(out) as tar:
        found_msg = False
        for m in tar.getmembers():
            if m.name.startswith("course/html/") and m.name.endswith(".html"):
                content = _read(tar, m.name)
                if "Audio không tồn tại" in content:
                    found_msg = True
                    break
        assert found_msg, "Audio unit không có file phải hiển thị thông báo an toàn"


@pytest.mark.anyio
async def test_export_openedx_endpoint_accepts_mp3():
    """Endpoint export_openedx phải tiếp nhận file .mp3 và đưa vào gói export."""
    from io import BytesIO
    from fastapi import UploadFile
    from app.api.v1.endpoints.export import export_openedx

    mp3_bytes = b"ID3_fake_audio_data"
    upload = UploadFile(filename="unit-audio-01.mp3", file=BytesIO(mp3_bytes))
    outline = json.dumps({"outline": OUTLINE_AUDIO_UNIT})
    questions = json.dumps([])

    resp = await export_openedx(
        files=[upload],
        outline=outline,
        questions=questions,
        filename="test_audio_endpoint_export"
    )
    assert resp.success is True
    assert resp.tar_file.endswith(".tar.gz")

    # Kiểm tra file tar thực tế được sinh ra
    tar_real_path = Path(BACKEND) / resp.tar_file.lstrip("/")
    if not tar_real_path.exists():
        # Thử đường dẫn từ thư mục backend
        tar_real_path = Path(BACKEND) / "exports" / Path(resp.tar_file).name

    if tar_real_path.exists():
        with tarfile.open(tar_real_path) as tar:
            members = _members(tar)
            assert "course/static/unit-audio-01.mp3" in members
            assets = json.loads(_read(tar, "course/policies/assets.json"))
            assert "unit-audio-01.mp3" in assets
            assert assets["unit-audio-01.mp3"]["contentType"] == "audio/mpeg"


# ===========================================================================
# T3: Outline Parser Excel Tests (Phương án A)
# ===========================================================================

import openpyxl
from io import BytesIO
from fastapi import UploadFile
from app.api.v1.endpoints.outline import import_outline_excel


@pytest.mark.anyio
async def test_outline_legacy_5_columns_backward_compatible():
    """File Excel cũ với đúng 5 cột (Chapter, Lesson, Unit, Slide, Youtube) hoạt động 100% bình thường."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Outline"
    ws.append(["Chapter", "Lesson", "Unit", "Slide", "Youtube"])
    ws.append(["Chương 1", "Bài 1", "Unit Slide", "slide1.pdf", ""])
    ws.append(["Chương 1", "Bài 1", "Unit Video", "", "https://youtu.be/abc12345678"])
    ws.append(["Chương 1", "Bài 1", "Unit Video+PDF", "slide2.pdf", "https://youtu.be/def12345678"])

    bio = BytesIO()
    wb.save(bio)
    bio.seek(0)

    upload = UploadFile(filename="legacy_outline.xlsx", file=bio)
    res = await import_outline_excel(file=upload)

    assert res.success is True, f"Import thất bại: {res.message}"
    chapters = res.outline.get("outline", [])
    assert len(chapters) == 1
    units = chapters[0]["subsections"][0]["units"]
    assert len(units) == 3

    assert units[0]["type"] == "pdf"
    assert units[0]["file"] == "slide1.pdf"

    assert units[1]["type"] == "video"
    assert units[1]["video_url"] == "https://youtu.be/abc12345678"

    assert units[2]["type"] == "video_pdf"
    assert units[2]["pdf_file"] == "slide2.pdf"


@pytest.mark.anyio
async def test_outline_new_columns_type_and_content():
    """File Excel mới có cột Type và Content: nhận diện chính xác các loại unit mới."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Outline"
    ws.append(["Chapter", "Lesson", "Unit", "Type", "Content", "Slide", "Youtube"])
    ws.append(["Chương 1", "Bài 1", "Unit Audio", "audio", "listen.mp3", "", ""])
    ws.append(["Chương 1", "Bài 1", "Unit Text", "text", "<p>Bài đọc văn bản</p>", "", ""])
    ws.append(["Chương 1", "Bài 1", "Unit Embed", "embed", '<iframe src="https://drive.google.com/xyz"></iframe>', "", ""])
    ws.append(["Chương 1", "Bài 1", "Unit PDF Direct", "pdf", "tailieu.pdf", "", ""])
    # Hàng Type để trống -> fallback về Slide
    ws.append(["Chương 1", "Bài 1", "Unit Fallback", "", "", "fallback.pdf", ""])

    bio = BytesIO()
    wb.save(bio)
    bio.seek(0)

    upload = UploadFile(filename="new_columns_outline.xlsx", file=bio)
    res = await import_outline_excel(file=upload)

    assert res.success is True, f"Import thất bại: {res.message}"
    chapters = res.outline.get("outline", [])
    units = chapters[0]["subsections"][0]["units"]
    assert len(units) == 5

    # 1. Audio
    assert units[0]["type"] == "audio"
    assert units[0]["audio_file"] == "listen.mp3"

    # 2. Text
    assert units[1]["type"] == "text"
    assert units[1]["html_content"] == "<p>Bài đọc văn bản</p>"

    # 3. Embed
    assert units[2]["type"] == "embed"
    assert 'iframe src="https://drive.google.com/xyz"' in units[2]["embed_code"]

    # 4. PDF
    assert units[3]["type"] == "pdf"
    assert units[3]["file"] == "tailieu.pdf"

    # 5. Fallback khi Type để trống
    assert units[4]["type"] == "pdf"
    assert units[4]["file"] == "fallback.pdf"


@pytest.mark.anyio
async def test_outline_csv_support_both_legacy_and_new():
    """Hỗ trợ CSV cho cả định dạng cũ (5 cột) và mới (có Type, Content)."""
    # 1. CSV mới có Type & Content
    csv_text = (
        "Chapter,Lesson,Unit,Type,Content,Slide,Youtube\n"
        "Chương 1,Bài 1,Nghe bài 1,audio,audio1.mp3,,\n"
        "Chương 1,Bài 1,Đọc bài 1,text,<p>Doc</p>,,\n"
    )
    bio = BytesIO(csv_text.encode("utf-8-sig"))
    upload = UploadFile(filename="outline.csv", file=bio)
    res = await import_outline_excel(file=upload)
    assert res.success is True
    units = res.outline["outline"][0]["subsections"][0]["units"]
    assert units[0]["type"] == "audio"
    assert units[0]["audio_file"] == "audio1.mp3"
    assert units[1]["type"] == "text"

    # 2. CSV cũ không có Type & Content
    csv_legacy = (
        "Chapter,Lesson,Unit,Slide,Youtube\n"
        "Chương 1,Bài 1,Slide 1,bai1.pdf,\n"
    )
    bio_legacy = BytesIO(csv_legacy.encode("utf-8-sig"))
    upload_legacy = UploadFile(filename="legacy.csv", file=bio_legacy)
    res_legacy = await import_outline_excel(file=upload_legacy)
    assert res_legacy.success is True
    units_legacy = res_legacy.outline["outline"][0]["subsections"][0]["units"]
    assert units_legacy[0]["type"] == "pdf"
    assert units_legacy[0]["file"] == "bai1.pdf"


@pytest.mark.anyio
async def test_outline_missing_required_headers_returns_error():
    """Thiếu cột bắt buộc (Chapter, Lesson hoặc Unit) phải trả về thông báo lỗi rõ ràng."""
    csv_bad = "Lesson,Unit,Slide\nBài 1,Unit 1,slide.pdf\n"
    bio = BytesIO(csv_bad.encode("utf-8"))
    upload = UploadFile(filename="bad.csv", file=bio)
    res = await import_outline_excel(file=upload)
    assert res.success is False
    assert "Thiếu cột bắt buộc" in res.message
    assert "Chapter" in res.message



