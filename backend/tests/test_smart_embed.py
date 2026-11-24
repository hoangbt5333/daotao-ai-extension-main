import sys
from pathlib import Path
BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import pytest
from unittest.mock import MagicMock, patch

from app.services.export.embed_helper import (
    convert_share_url_to_embed_url,
    build_embed_iframe,
    sanitize_embed_html,
    resolve_sharepoint_redirect,
    is_shortened_sharepoint_url,
    is_embed_content,
)
from app.services.export.openedx import OpenEdXExporter


# ============================================================================
# Hướng 1: Static pattern matching tests
# ============================================================================

class TestGoogleWorkspaceEmbed:
    def test_gdrive_file_view(self):
        url = "https://drive.google.com/file/d/1ABCxyz_123/view?usp=sharing"
        assert convert_share_url_to_embed_url(url) == "https://drive.google.com/file/d/1ABCxyz_123/preview"

    def test_gdrive_open_id(self):
        url = "https://drive.google.com/open?id=1ABCxyz_123"
        assert convert_share_url_to_embed_url(url) == "https://drive.google.com/file/d/1ABCxyz_123/preview"

    def test_gdrive_uc_id(self):
        url = "https://drive.google.com/uc?id=1ABCxyz_123"
        assert convert_share_url_to_embed_url(url) == "https://drive.google.com/file/d/1ABCxyz_123/preview"

    def test_gdrive_already_preview(self):
        url = "https://drive.google.com/file/d/1ABCxyz_123/preview"
        assert convert_share_url_to_embed_url(url) == "https://drive.google.com/file/d/1ABCxyz_123/preview"

    def test_google_docs(self):
        url = "https://docs.google.com/document/d/1xyzDocID/edit?usp=sharing"
        assert convert_share_url_to_embed_url(url) == "https://docs.google.com/document/d/1xyzDocID/preview"

    def test_google_sheets(self):
        url = "https://docs.google.com/spreadsheets/d/1xyzSheetID/edit#gid=0"
        assert convert_share_url_to_embed_url(url) == "https://docs.google.com/spreadsheets/d/1xyzSheetID/preview"

    def test_google_slides(self):
        url = "https://docs.google.com/presentation/d/1xyzSlideID/edit?usp=sharing"
        assert convert_share_url_to_embed_url(url) == "https://docs.google.com/presentation/d/1xyzSlideID/embed"

    def test_google_forms(self):
        url1 = "https://docs.google.com/forms/d/e/1FAIpQLSc_test_123/viewform?usp=sf_link"
        res1 = convert_share_url_to_embed_url(url1)
        assert "embedded=true" in res1
        assert "1FAIpQLSc_test_123" in res1

        url2 = "https://docs.google.com/forms/d/e/1FAIpQLSc_test_123/viewform"
        res2 = convert_share_url_to_embed_url(url2)
        assert res2 == "https://docs.google.com/forms/d/e/1FAIpQLSc_test_123/viewform?embedded=true"


class TestMicrosoft365Embed:
    def test_sharepoint_doc_aspx_replaces_action(self):
        url = "https://husteduvn-my.sharepoint.com/personal/abc_hust_edu_vn/_layouts/15/Doc.aspx?sourcedoc={452F791F-AD42-407C-A80F-F86F050D6457}&action=default&mobileredirect=true"
        res = convert_share_url_to_embed_url(url)
        assert "action=embedview" in res
        assert "action=default" not in res
        assert "sourcedoc={452F791F-AD42-407C-A80F-F86F050D6457}" in res

    def test_sharepoint_doc_aspx_appends_action(self):
        url = "https://husteduvn-my.sharepoint.com/:w:/r/personal/user/_layouts/15/Doc.aspx?sourcedoc=%7B452F791F%7D&file=test.docx"
        res = convert_share_url_to_embed_url(url)
        assert "action=embedview" in res
        assert "sourcedoc=%7B452F791F%7D" in res

    def test_sharepoint_doc_aspx_already_embedview(self):
        url = "https://husteduvn-my.sharepoint.com/personal/user/_layouts/15/Doc.aspx?sourcedoc={452F791F}&action=embedview"
        res = convert_share_url_to_embed_url(url)
        assert res == url

    def test_stream_sharepoint_appends_embed(self):
        url = "https://husteduvn.sharepoint.com/sites/team/Stream.aspx?id=%2Fsites%2Fvideo.mp4"
        res = convert_share_url_to_embed_url(url)
        assert res == "https://husteduvn.sharepoint.com/sites/team/Stream.aspx?id=%2Fsites%2Fvideo.mp4&embed=1"

    def test_stream_sharepoint_already_embed(self):
        url = "https://husteduvn.sharepoint.com/sites/team/Stream.aspx?id=%2Fsites%2Fvideo.mp4&embed=1"
        assert convert_share_url_to_embed_url(url) == url

    def test_stream_classic(self):
        url = "https://web.microsoftstream.com/video/abcdef-1234-5678-90"
        assert convert_share_url_to_embed_url(url) == "https://web.microsoftstream.com/embed/video/abcdef-1234-5678-90?autoplay=false&showinfo=true"


class TestMediaAndOtherEmbed:
    def test_youtube_watch(self):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert convert_share_url_to_embed_url(url) == "https://www.youtube.com/embed/dQw4w9WgXcQ"

    def test_youtube_short_link(self):
        url = "https://youtu.be/dQw4w9WgXcQ"
        assert convert_share_url_to_embed_url(url) == "https://www.youtube.com/embed/dQw4w9WgXcQ"

    def test_youtube_shorts(self):
        url = "https://www.youtube.com/shorts/dQw4w9WgXcQ"
        assert convert_share_url_to_embed_url(url) == "https://www.youtube.com/embed/dQw4w9WgXcQ"

    def test_youtube_with_timestamp(self):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=90s"
        assert convert_share_url_to_embed_url(url) == "https://www.youtube.com/embed/dQw4w9WgXcQ?start=90"

        url2 = "https://youtu.be/dQw4w9WgXcQ?t=1m30s"
        assert convert_share_url_to_embed_url(url2) == "https://www.youtube.com/embed/dQw4w9WgXcQ?start=90"

    def test_vimeo(self):
        url = "https://vimeo.com/123456789"
        assert convert_share_url_to_embed_url(url) == "https://player.vimeo.com/video/123456789"

    def test_loom(self):
        url = "https://www.loom.com/share/abc123xyz"
        assert convert_share_url_to_embed_url(url) == "https://loom.com/embed/abc123xyz"

    def test_canva(self):
        url = "https://www.canva.com/design/DAFxyz123/view"
        assert convert_share_url_to_embed_url(url) == "https://www.canva.com/design/DAFxyz123/view?embed"

    def test_quizlet(self):
        url = "https://quizlet.com/123456789/my-flashcards/"
        assert convert_share_url_to_embed_url(url) == "https://quizlet.com/123456789/flashcards/embed"

    def test_unknown_url_unchanged(self):
        url = "https://example.com/custom/page.html"
        assert convert_share_url_to_embed_url(url) == url


class TestBuildEmbedIframe:
    def test_plain_url_gdrive(self):
        url = "https://drive.google.com/file/d/1ABC_999/view"
        iframe = build_embed_iframe(url)
        assert 'src="https://drive.google.com/file/d/1ABC_999/preview"' in iframe
        assert 'width="1200"' in iframe
        assert 'height="640"' in iframe
        assert 'allow="autoplay"' in iframe

    def test_plain_url_sharepoint(self):
        url = "https://tenant.sharepoint.com/Doc.aspx?sourcedoc={123}&action=default"
        iframe = build_embed_iframe(url)
        assert 'src="https://tenant.sharepoint.com/Doc.aspx?sourcedoc={123}&amp;action=embedview"' in iframe or 'action=embedview' in iframe
        assert 'width="900"' in iframe
        assert 'height="640"' in iframe
        assert 'allowfullscreen' in iframe

    def test_plain_url_youtube(self):
        url = "https://youtu.be/dQw4w9WgXcQ"
        iframe = build_embed_iframe(url)
        assert 'src="https://www.youtube.com/embed/dQw4w9WgXcQ"' in iframe
        assert 'allowfullscreen' in iframe

    def test_existing_iframe_with_share_url(self):
        raw = '<iframe src="https://drive.google.com/file/d/1ABC_999/view?usp=sharing" width="800" height="500"></iframe>'
        result = build_embed_iframe(raw)
        assert 'src="https://drive.google.com/file/d/1ABC_999/preview"' in result
        assert 'width="800"' in result
        assert 'height="500"' in result

    def test_existing_iframe_with_sharepoint_url(self):
        raw = '<iframe src="https://tenant.sharepoint.com/Doc.aspx?sourcedoc={123}&amp;action=default" width="600" height="400"></iframe>'
        result = build_embed_iframe(raw)
        assert 'action=embedview' in result
        assert 'action=default' not in result
        # Custom user-defined size 600x400 should be preserved
        assert 'width="600"' in result
        assert 'height="400"' in result

    def test_sharepoint_default_tiny_size_auto_upgrades_to_900x640(self):
        raw = '<iframe src="https://tenant.sharepoint.com/Doc.aspx?sourcedoc={123}&amp;action=default" width="476px" height="288px" frameborder="0"></iframe>'
        result = build_embed_iframe(raw)
        assert 'width="900"' in result
        assert 'height="640"' in result
        assert '476px' not in result
        assert '288px' not in result

    def test_sharepoint_iframe_missing_dimensions_auto_adds_900x640(self):
        raw = '<iframe src="https://tenant.sharepoint.com/Doc.aspx?sourcedoc={123}"></iframe>'
        result = build_embed_iframe(raw)
        assert 'width="900"' in result
        assert 'height="640"' in result


class TestSanitizeEmbedHtml:
    def test_strips_scripts_and_events(self):
        malicious = (
            '<script>alert("xss")</script>'
            '<iframe src="https://example.com" onload="alert(1)" onerror="alert(2)"></iframe>'
            '<a href="javascript:steal()">Click</a>'
        )
        clean = sanitize_embed_html(malicious)
        assert "<script>" not in clean
        assert "alert" not in clean
        assert "onload" not in clean
        assert "onerror" not in clean
        assert "javascript:" not in clean
        assert '<iframe src="https://example.com">' in clean or '<iframe src="https://example.com"' in clean

    def test_empty_string(self):
        assert sanitize_embed_html("") == "<p>Nội dung nhúng không tồn tại.</p>"
        assert sanitize_embed_html("   ") == "<p>Nội dung nhúng không tồn tại.</p>"


# ============================================================================
# Hướng 2: Redirect resolver tests
# ============================================================================

class TestSharePointRedirectResolver:
    def test_is_shortened_sharepoint_url(self):
        assert is_shortened_sharepoint_url("https://1drv.ms/p/s!Amx123")
        assert is_shortened_sharepoint_url("https://1drv.ms/b/s!Amx456")
        assert is_shortened_sharepoint_url("https://forms.gle/XYZ12345")
        assert is_shortened_sharepoint_url("https://husteduvn-my.sharepoint.com/:p:/g/personal/user/Eabcdef123")
        assert is_shortened_sharepoint_url("https://husteduvn-my.sharepoint.com/:w:/g/personal/user/Eabcdef123")
        assert is_shortened_sharepoint_url("https://husteduvn-my.sharepoint.com/:x:/g/personal/user/Eabcdef123")
        assert not is_shortened_sharepoint_url("https://husteduvn-my.sharepoint.com/personal/user/Doc.aspx?sourcedoc={123}")
        assert not is_shortened_sharepoint_url("https://drive.google.com/file/d/123/view")

    def test_resolver_follows_redirect_and_converts_to_embed(self):
        short_url = "https://1drv.ms/p/s!Amx123"
        resolved_url = "https://tenant.sharepoint.com/personal/user/_layouts/15/Doc.aspx?sourcedoc={ABC-123}&file=pres.pptx&action=default"

        mock_response = MagicMock()
        mock_response.url = resolved_url

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            # Mock client.stream context manager
            mock_stream_ctx = MagicMock()
            mock_stream_ctx.__enter__.return_value = mock_response
            mock_client.stream.return_value = mock_stream_ctx
            mock_client_cls.return_value = mock_client

            final_url = resolve_sharepoint_redirect(short_url)
            assert "action=embedview" in final_url
            assert "{ABC-123}" in final_url

    def test_resolver_fallback_on_network_error(self):
        short_url = "https://1drv.ms/p/s!Amx123"
        with patch("httpx.Client", side_effect=Exception("Network unreachable")):
            fallback_url = resolve_sharepoint_redirect(short_url)
            # Should gracefully fallback to original URL
            assert fallback_url == short_url


# ============================================================================
# Integration with OpenEdXCourseExporter
# ============================================================================

class TestExporterIntegration:
    def test_sanitize_embed_delegates_to_smart_embed(self):
        exporter = OpenEdXExporter()
        
        # Test Google Slides share URL
        slides_url = "https://docs.google.com/presentation/d/1A_B_C/edit?usp=sharing"
        html = exporter._sanitize_embed(slides_url)
        assert 'src="https://docs.google.com/presentation/d/1A_B_C/embed"' in html
        assert "<iframe" in html

        # Test SharePoint share URL
        sp_url = "https://husteduvn-my.sharepoint.com/personal/user/_layouts/15/Doc.aspx?sourcedoc={UUID}&action=default"
        html_sp = exporter._sanitize_embed(sp_url)
        assert "action=embedview" in html_sp
        assert "action=default" not in html_sp


class TestIsEmbedContent:
    def test_detects_iframe(self):
        assert is_embed_content('<iframe src="https://example.com"></iframe>')
        assert is_embed_content('  <IFRAME SRC="https://drive.google.com/test"></IFRAME>  ')

    def test_detects_cloud_links(self):
        assert is_embed_content("https://drive.google.com/file/d/123/view")
        assert is_embed_content("https://docs.google.com/document/d/abc/edit")
        assert is_embed_content("https://docs.google.com/spreadsheets/d/xyz/edit")
        assert is_embed_content("https://docs.google.com/presentation/d/uvw/edit")
        assert is_embed_content("https://husteduvn-my.sharepoint.com/personal/abc/Doc.aspx?sourcedoc={123}")
        assert is_embed_content("https://1drv.ms/p/s!Amx123")
        assert is_embed_content("https://forms.gle/XYZ123")
        assert is_embed_content("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

    def test_rejects_non_embed_content(self):
        assert not is_embed_content("bai_giang_so_1.pdf")
        assert not is_embed_content("audio_lesson.mp3")
        assert not is_embed_content("<p>Đây là bài học văn bản HTML</p>")
        assert not is_embed_content("Nội dung tóm tắt chương 1")


class TestTemplateEmbedRowsAndAutoDetect:
    @pytest.mark.anyio
    async def test_template_contains_both_iframe_and_share_link_examples(self):
        from io import BytesIO
        from openpyxl import load_workbook
        from app.api.v1.endpoints.outline import download_outline_template

        resp = await download_outline_template()
        wb = load_workbook(BytesIO(resp.body), data_only=True)
        ws = wb["Mẫu"]
        rows = list(ws.iter_rows(min_row=2, values_only=True))

        # Check for embed rows
        embed_rows = [r for r in rows if r[3] == "embed"]
        assert len(embed_rows) >= 2, "Cần có cả 2 dòng ví dụ cho embed: 1 dòng iframe và 1 dòng link share"

        # One row has iframe
        has_iframe = any("<iframe" in (r[4] or "") for r in embed_rows)
        # One row has direct share URL
        has_share_url = any("view?usp=sharing" in (r[4] or "") for r in embed_rows)

        assert has_iframe, "Thiếu dòng ví dụ mã nhúng <iframe> cho embed trong sheet Mẫu"
        assert has_share_url, "Thiếu dòng ví dụ đường link chia sẻ trực tiếp cho embed trong sheet Mẫu"

    @pytest.mark.anyio
    async def test_auto_detect_embed_when_type_column_is_empty(self):
        from io import BytesIO
        from openpyxl import Workbook
        from fastapi import UploadFile
        from app.api.v1.endpoints.outline import import_outline_excel

        wb = Workbook()
        ws = wb.active
        ws.title = "Outline"
        ws.append(["Chapter", "Lesson", "Unit", "Type", "Content", "Slide", "Youtube"])
        ws.append([
            "Chương 1", "Bài 1", "Unit 1 Embed Iframe", "",
            '<iframe src="https://drive.google.com/file/d/1ABC/preview"></iframe>', "", ""
        ])
        ws.append([
            "", "", "Unit 2 Embed Share Link", "",
            "https://drive.google.com/file/d/1XYZ/view?usp=sharing", "", ""
        ])

        bio = BytesIO()
        wb.save(bio)
        bio.seek(0)

        upload = UploadFile(filename="autodetect.xlsx", file=bio)
        res = await import_outline_excel(upload)

        assert res.success is True
        units = res.outline["outline"][0]["subsections"][0]["units"]
        assert len(units) == 2
        assert units[0]["type"] == "embed"
        assert '<iframe src="https://drive.google.com/file/d/1ABC/preview">' in units[0]["embed_code"]
        assert units[1]["type"] == "embed"
        assert "https://drive.google.com/file/d/1XYZ/view?usp=sharing" in units[1]["embed_code"]


class TestLinkAndTextEnhancements:
    def test_format_text_content_plain_text(self):
        exporter = OpenEdXExporter()
        raw = "Đoạn văn thứ nhất.\nĐoạn văn thứ hai."
        res = exporter._format_text_content(raw)
        assert res == "<p>Đoạn văn thứ nhất.</p>\n<p>Đoạn văn thứ hai.</p>"

    def test_format_text_content_preserves_existing_html(self):
        exporter = OpenEdXExporter()
        raw = "<div><p>Đã có <b>thẻ HTML</b></p></div>"
        res = exporter._format_text_content(raw)
        assert res == raw

    def test_format_text_content_linkifies_bare_url(self):
        exporter = OpenEdXExporter()
        raw = "https://hust.edu.vn"
        res = exporter._format_text_content(raw)
        assert '<a href="https://hust.edu.vn" target="_blank" rel="noopener noreferrer">https://hust.edu.vn</a>' in res

    @pytest.mark.anyio
    async def test_link_unit_import_excel(self):
        from io import BytesIO
        from openpyxl import Workbook
        from fastapi import UploadFile
        from app.api.v1.endpoints.outline import import_outline_excel

        wb = Workbook()
        ws = wb.active
        ws.title = "Outline"
        ws.append(["Chapter", "Lesson", "Unit", "Type", "Content", "Slide", "Youtube"])
        ws.append([
            "Chương 1", "Bài 1", "Unit Liên Kết Ngoài", "link",
            "https://hust.edu.vn", "", ""
        ])

        bio = BytesIO()
        wb.save(bio)
        bio.seek(0)

        upload = UploadFile(filename="link.xlsx", file=bio)
        res = await import_outline_excel(upload)

        assert res.success is True
        units = res.outline["outline"][0]["subsections"][0]["units"]
        assert len(units) == 1
        assert units[0]["type"] == "link"
        assert units[0]["link_url"] == "https://hust.edu.vn"

    @pytest.mark.anyio
    async def test_auto_detect_link_when_type_empty_and_url_not_embed(self):
        from io import BytesIO
        from openpyxl import Workbook
        from fastapi import UploadFile
        from app.api.v1.endpoints.outline import import_outline_excel

        wb = Workbook()
        ws = wb.active
        ws.title = "Outline"
        ws.append(["Chapter", "Lesson", "Unit", "Type", "Content", "Slide", "Youtube"])
        ws.append([
            "Chương 1", "Bài 1", "Unit Auto Link", "",
            "https://hust.edu.vn", "", ""
        ])

        bio = BytesIO()
        wb.save(bio)
        bio.seek(0)

        upload = UploadFile(filename="autolink.xlsx", file=bio)
        res = await import_outline_excel(upload)

        assert res.success is True
        units = res.outline["outline"][0]["subsections"][0]["units"]
        assert len(units) == 1
        assert units[0]["type"] == "link"
        assert units[0]["link_url"] == "https://hust.edu.vn"

    def test_build_link_component_html(self):
        exporter = OpenEdXExporter()
        html = exporter._build_link_component_html("Bài học liên kết", "https://hust.edu.vn")
        assert 'href="https://hust.edu.vn"' in html
        assert 'target="_blank"' in html
        assert 'rel="noopener noreferrer"' in html
        assert "Truy cập liên kết" in html


