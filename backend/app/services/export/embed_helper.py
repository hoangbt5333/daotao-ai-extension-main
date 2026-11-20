import re
import html
import logging
from typing import Optional
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

import httpx

logger = logging.getLogger(__name__)

# Pattern for shortened OneDrive / SharePoint / Google Forms URLs
SHORTENED_URL_PATTERN = re.compile(
    r'https?://(?:1drv\.ms/[a-zA-Z0-9!_/-]+|[a-zA-Z0-9.-]+\.sharepoint\.com/:(?:[a-zA-Z]):/[a-zA-Z]/[a-zA-Z0-9_-]+|forms\.gle/[a-zA-Z0-9_-]+)',
    re.IGNORECASE
)
SHORTENED_SHAREPOINT_PATTERN = SHORTENED_URL_PATTERN


def is_shortened_sharepoint_url(url: str) -> bool:
    """Check if URL is a shortened OneDrive, SharePoint, or Forms sharing link."""
    if not url:
        return False
    return bool(SHORTENED_URL_PATTERN.search(url.strip()))


is_shortened_url = is_shortened_sharepoint_url


def resolve_sharepoint_redirect(url: str, timeout: float = 3.0) -> str:
    """Resolve shortened SharePoint / OneDrive / Forms sharing link to target URL.
    
    If network error, timeout, or non-redirect, safely falls back to original URL.
    """
    cleaned = (url or "").strip()
    if not is_shortened_sharepoint_url(cleaned):
        return cleaned

    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
        with httpx.Client(follow_redirects=True, timeout=timeout, headers=headers) as client:
            with client.stream("GET", cleaned) as response:
                resolved = str(response.url)
                if resolved and resolved != cleaned:
                    logger.info("Resolved shortened URL %s -> %s", cleaned, resolved)
                    return convert_share_url_to_embed_url(resolved)
    except Exception as e:
        logger.warning("Failed to resolve redirect for %s: %s. Using original URL.", cleaned, e)

    return cleaned


resolve_redirect_url = resolve_sharepoint_redirect


def convert_share_url_to_embed_url(url: str) -> str:
    """Convert common sharing links into their iframe embeddable URL format.
    
    Supports:
    - Google Drive (file preview)
    - Google Docs, Sheets, Slides (preview / embed)
    - Google Forms (embedded=true)
    - Microsoft SharePoint / OneDrive Doc.aspx (action=embedview)
    - Microsoft Stream on SharePoint (embed=1)
    - Microsoft Stream Classic (web.microsoftstream.com/embed/video/...)
    - YouTube (embed/ID)
    - Vimeo (player.vimeo.com/video/ID)
    - Loom (loom.com/embed/ID)
    - Canva (canva.com/design/.../view?embed)
    - Quizlet (quizlet.com/.../flashcards/embed)
    """
    raw = (url or "").strip()
    if not raw:
        return ""

    # Unescape any HTML entities if already escaped (&amp; -> &)
    raw = html.unescape(raw)

    # 1. Google Drive files
    # Formats:
    # - https://drive.google.com/file/d/{id}/view...
    # - https://drive.google.com/open?id={id}
    # - https://drive.google.com/uc?id={id}
    gdrive_match = re.search(r'drive\.google\.com/(?:file/d/|open\?id=|uc\?id=)([a-zA-Z0-9_-]+)', raw)
    if gdrive_match:
        file_id = gdrive_match.group(1)
        return f"https://drive.google.com/file/d/{file_id}/preview"

    # 2. Google Docs
    # https://docs.google.com/document/d/{id}/...
    gdoc_match = re.search(r'docs\.google\.com/document/d/([a-zA-Z0-9_-]+)', raw)
    if gdoc_match:
        doc_id = gdoc_match.group(1)
        return f"https://docs.google.com/document/d/{doc_id}/preview"

    # 3. Google Sheets
    # https://docs.google.com/spreadsheets/d/{id}/...
    gsheet_match = re.search(r'docs\.google\.com/spreadsheets/d/([a-zA-Z0-9_-]+)', raw)
    if gsheet_match:
        sheet_id = gsheet_match.group(1)
        return f"https://docs.google.com/spreadsheets/d/{sheet_id}/preview"

    # 4. Google Slides
    # https://docs.google.com/presentation/d/{id}/...
    gslide_match = re.search(r'docs\.google\.com/presentation/d/([a-zA-Z0-9_-]+)', raw)
    if gslide_match:
        slide_id = gslide_match.group(1)
        return f"https://docs.google.com/presentation/d/{slide_id}/embed"

    # 5. Google Forms
    # https://docs.google.com/forms/d/(?:e/)?{id}/viewform...
    if "docs.google.com/forms" in raw:
        if "embedded=true" not in raw:
            sep = "&" if "?" in raw else "?"
            return f"{raw}{sep}embedded=true"
        return raw

    # 6. Microsoft SharePoint / OneDrive Doc.aspx (Office Online Word, Excel, PPT)
    # Target: ensure action=embedview
    if "Doc.aspx" in raw or ("sharepoint.com" in raw and "sourcedoc=" in raw):
        if "action=" in raw:
            # Replace any existing action with embedview
            converted = re.sub(r'([?&])action=[^&#]+', r'\1action=embedview', raw)
            return converted
        else:
            sep = "&" if "?" in raw else "?"
            return f"{raw}{sep}action=embedview"

    # 7. Microsoft Stream (on SharePoint)
    # https://tenant.sharepoint.com/.../Stream.aspx?id=...
    if "Stream.aspx" in raw:
        if "embed=1" not in raw:
            sep = "&" if "?" in raw else "?"
            return f"{raw}{sep}embed=1"
        return raw

    # 8. Microsoft Stream (Classic)
    # https://web.microsoftstream.com/video/{video_id}
    stream_classic_match = re.search(r'web\.microsoftstream\.com/video/([a-zA-Z0-9_-]+)', raw)
    if stream_classic_match:
        v_id = stream_classic_match.group(1)
        return f"https://web.microsoftstream.com/embed/video/{v_id}?autoplay=false&showinfo=true"

    # 9. YouTube
    # https://www.youtube.com/watch?v={id}, https://youtu.be/{id}, https://www.youtube.com/shorts/{id}
    yt_match = re.search(r'(?:youtube\.com/(?:watch\?.*v=|embed/|v/|shorts/)|youtu\.be/)([a-zA-Z0-9_-]{11})', raw)
    if yt_match:
        yt_id = yt_match.group(1)
        # Check for timestamp (e.g. t=90, t=1m30s, start=90)
        t_match = re.search(r'[?&](?:t|start)=([0-9a-zA-Z]+)', raw)
        start_sec = None
        if t_match:
            raw_t = t_match.group(1)
            try:
                if raw_t.isdigit():
                    start_sec = int(raw_t)
                else:
                    h = re.search(r'(\d+)h', raw_t)
                    m = re.search(r'(\d+)m', raw_t)
                    s = re.search(r'(\d+)s', raw_t)
                    sec = 0
                    if h:
                        sec += int(h.group(1)) * 3600
                    if m:
                        sec += int(m.group(1)) * 60
                    if s:
                        sec += int(s.group(1))
                    start_sec = sec if sec > 0 else None
            except Exception:
                start_sec = None

        if start_sec:
            return f"https://www.youtube.com/embed/{yt_id}?start={start_sec}"
        return f"https://www.youtube.com/embed/{yt_id}"

    # 10. Vimeo
    # https://vimeo.com/{id}
    vimeo_match = re.search(r'(?:vimeo\.com/|player\.vimeo\.com/video/)(\d+)', raw)
    if vimeo_match:
        v_id = vimeo_match.group(1)
        return f"https://player.vimeo.com/video/{v_id}"

    # 11. Loom
    # https://www.loom.com/share/{id}
    loom_match = re.search(r'loom\.com/(?:share|embed)/([a-zA-Z0-9_-]+)', raw)
    if loom_match:
        l_id = loom_match.group(1)
        return f"https://loom.com/embed/{l_id}"

    # 12. Canva
    # https://www.canva.com/design/{id}/view...
    canva_match = re.search(r'canva\.com/design/([a-zA-Z0-9_-]+)/view', raw)
    if canva_match:
        if "embed" not in raw:
            sep = "&" if "?" in raw else "?"
            return f"{raw}{sep}embed"
        return raw

    # 13. Quizlet
    # https://quizlet.com/{id}/...
    quizlet_match = re.search(r'quizlet\.com/(\d+)(?:/[^/?#]+)?', raw)
    if quizlet_match and "embed" not in raw:
        q_id = quizlet_match.group(1)
        return f"https://quizlet.com/{q_id}/flashcards/embed"

    # Unrecognized / already direct embed URL
    return raw


def sanitize_embed_html(raw_html: str) -> str:
    """Sanitize HTML embed code to prevent XSS and upgrade inner iframe src.
    
    1. Upgrades any inner <iframe src="..."> link from a share link to an embed link.
    2. Strips <script> and <style> tags.
    3. Strips inline JS event handlers (onload, onerror, onclick, etc.).
    4. Strips javascript: URLs.
    """
    raw = (raw_html or "").strip()
    if not raw:
        return "<p>Nội dung nhúng không tồn tại.</p>"

    # 1. Upgrade iframe src links
    def _replace_iframe_src(match: re.Match) -> str:
        iframe_tag = match.group(0)
        src_match = re.search(r'src=(["\'])(.*?)\1', iframe_tag, re.IGNORECASE)
        if not src_match:
            return iframe_tag
        quote = src_match.group(1)
        old_src = src_match.group(2)
        
        # Resolve redirect if shortened SharePoint
        if is_shortened_sharepoint_url(old_src):
            old_src = resolve_sharepoint_redirect(old_src)
            
        new_src = convert_share_url_to_embed_url(old_src)
        # Escape quotes in src
        safe_src = new_src.replace('"', '&quot;') if quote == '"' else new_src.replace("'", "&#39;")
        return re.sub(r'src=(["\']).*?\1', f'src={quote}{safe_src}{quote}', iframe_tag, count=1, flags=re.IGNORECASE)

    updated_html = re.sub(r'<iframe\b[^>]*>', _replace_iframe_src, raw, flags=re.IGNORECASE)

    # 2. XSS Sanitization
    sanitized = re.sub(r'<\s*script[^>]*>.*?<\s*/\s*script\s*>', '', updated_html, flags=re.IGNORECASE | re.DOTALL)
    sanitized = re.sub(r'<\s*style[^>]*>.*?<\s*/\s*style\s*>', '', sanitized, flags=re.IGNORECASE | re.DOTALL)
    sanitized = re.sub(r'\s+on[a-zA-Z]+\s*=\s*(?:"[^"]*"|\'[^\']*\'|[^\s>]+)', '', sanitized)
    sanitized = re.sub(r'(src|href)\s*=\s*["\']\s*javascript:[^"\']*["\']', '', sanitized, flags=re.IGNORECASE)

    return sanitized.strip()


def build_embed_iframe(code_or_url: str, title: str = "") -> str:
    """Build a safe <iframe> or sanitize user-provided HTML embed code.
    
    If pure URL:
    - Automatically resolves shortened links (SharePoint / OneDrive).
    - Converts share link to embed URL.
    - Wraps in proper responsive / Open edX-compatible iframe markup.
    
    If HTML snippet:
    - Runs sanitize_embed_html (upgrades iframe src and strips XSS vectors).
    """
    raw = (code_or_url or "").strip()
    if not raw:
        return "<p>Nội dung nhúng không tồn tại.</p>"

    # Check if pure URL
    if raw.startswith(("http://", "https://")) and "<" not in raw:
        url = raw
        if is_shortened_sharepoint_url(url):
            url = resolve_sharepoint_redirect(url)

        embed_url = convert_share_url_to_embed_url(url)
        escaped_url = embed_url.replace('"', '&quot;')

        # Google Drive: per HUST guidelines & existing code (1200x640, allow="autoplay")
        if "drive.google.com" in embed_url:
            return f'<iframe src="{escaped_url}" width="1200" height="640" allow="autoplay" allowfullscreen></iframe>'

        # Video players (YouTube, Vimeo, Loom): allow media controls
        if any(v in embed_url for v in ("youtube.com", "vimeo.com", "loom.com")):
            return (
                f'<iframe src="{escaped_url}" width="100%" height="600px" frameborder="0" '
                f'allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" '
                f'allowfullscreen></iframe>'
            )

        # SharePoint / Office / Google Docs / Sheets / Slides / Generic
        return f'<iframe src="{escaped_url}" width="100%" height="600px" frameborder="0" allowfullscreen></iframe>'

    # HTML snippet
    return sanitize_embed_html(raw)
