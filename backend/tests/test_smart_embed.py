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
