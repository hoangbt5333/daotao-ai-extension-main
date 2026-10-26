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
