"""
OpenEdX export service
"""
import os
import re
import uuid
import tempfile
import tarfile
import shutil
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse, parse_qs
from app.services.export.base import Exporter
from app.core.logging import get_logger


class OpenEdXExporter(Exporter):
    """OpenEdX course export service"""
    
    def __init__(self):
        super().__init__("openedx")
    
    def get_supported_formats(self) -> List[str]:
        return ["tar.gz"]
    
    def validate_data(self, data: Dict[str, Any]) -> bool:
        """Validate OpenEdX export data"""
        required_keys = ["outline", "questions"]
        if not all(key in data for key in required_keys):
            return False
        
        # Validate outline structure
        outline = data.get("outline", [])
        if not isinstance(outline, list) or len(outline) == 0:
            return False
        
        # Validate questions
        questions = data.get("questions", [])
        if not isinstance(questions, list):
            return False
        
        return True
    
    def export(self, data: Dict[str, Any], output_path: str) -> bool:
        """Export to OpenEdX format"""
        try:
            # Create temporary directory
            temp_dir = tempfile.mkdtemp()
            
            try:
                # Create directory structure
                self._create_directory_structure(temp_dir)
                
                # Export course structure
                self._export_course_structure(data, temp_dir)
                
                # Create tar.gz file
                self._create_tarfile(temp_dir, output_path)
                
                return True
                
            finally:
                # Clean up temporary directory
                shutil.rmtree(temp_dir, ignore_errors=True)
                
        except Exception as e:
            self.logger.error(f"Error exporting OpenEdX course: {e}")
            return False
    
    def _create_directory_structure(self, base_path: str):
        """Create OpenEdX directory structure"""
        # Create course directory first
        course_dir = os.path.join(base_path, "course")
        os.makedirs(course_dir, exist_ok=True)
        
        # Create subdirectories inside course
        directories = [
            "about", "chapter", "sequential", "vertical", 
            "problem", "video", "static", "policies", "html", "info", "assets", "drafts"
        ]
        
        for directory in directories:
            os.makedirs(os.path.join(course_dir, directory), exist_ok=True)
    
    def _export_course_structure(self, data: Dict[str, Any], output_dir: str):
        """Export course structure to OpenEdX format"""
        outline = data.get("outline", [])
        questions = data.get("questions", [])
        uploaded_assets = data.get("uploaded_assets") or data.get("uploaded_pdfs", [])
        
        # Get course directory path
        course_dir = os.path.join(output_dir, 'course')
        self.current_course_dir = course_dir  # Store for video XML creation
        
        # Process outline and create XML files
        chapter_ids = []
        sequential_ids = []
        vertical_ids = []
        
        # Create chapters
        for chapter_idx, chapter in enumerate(outline):
            chapter_id = self._generate_uuid()
            chapter_ids.append(chapter_id)
            
            chapter_sequential_ids = []
            
            # Create subsections (sequentials)
            for subsection_idx, subsection in enumerate(chapter.get('subsections', [])):
                sequential_id = self._generate_uuid()
                chapter_sequential_ids.append(sequential_id)
                sequential_ids.append(sequential_id)
                
                sequential_vertical_ids = []
                
                # Create units (verticals)
                for unit_idx, unit in enumerate(subsection.get('units', [])):
                    vertical_id = self._generate_uuid()
                    sequential_vertical_ids.append(vertical_id)
                    vertical_ids.append(vertical_id)
                    
                    # Create vertical XML
                    vertical_xml = self._create_vertical_xml(unit.get('title', 'Untitled Unit'), unit, vertical_id)
                    with open(os.path.join(course_dir, 'vertical', f'{vertical_id}.xml'), 'w', encoding='utf-8') as f:
                        f.write(vertical_xml)
                
                # Create sequential XML with vertical references
                sequential_xml = self._create_sequential_xml_with_references(subsection.get('title', 'Untitled Subsection'), sequential_vertical_ids)
                with open(os.path.join(course_dir, 'sequential', f'{sequential_id}.xml'), 'w', encoding='utf-8') as f:
                    f.write(sequential_xml)
            
            # Create chapter XML with sequential references
            chapter_xml = self._create_chapter_xml_with_references(chapter.get('title', 'Untitled Chapter'), chapter_sequential_ids)
            with open(os.path.join(course_dir, 'chapter', f'{chapter_id}.xml'), 'w', encoding='utf-8') as f:
                f.write(chapter_xml)
        
        # Create problems from questions
        self._create_problems_from_questions(questions, course_dir)
        
        # Copy uploaded assets (PDF, MP3, ...) to static directory
        self._copy_assets_to_static(uploaded_assets, course_dir)
        
        # Create policies/assets.json
        self._create_assets_json(course_dir)
        
        # Create final course.xml with chapter references
        self._create_final_course_xml(course_dir, chapter_ids)
    
    def _generate_uuid(self) -> str:
        """Generate UUID for OpenEdX components"""
        return str(uuid.uuid4()).replace('-', '')
    
    def _create_course_xml(self) -> str:
        """Create course.xml file"""
        course_elem = ET.Element("course")
        course_elem.set("url_name", "2024-May")
        course_elem.set("org", "SoDiTEC")
        course_elem.set("course", "TDC01")
        return ET.tostring(course_elem, encoding='unicode')
    
    def _create_final_course_xml(self, course_dir: str, chapter_ids: List[str]):
        """Create final course.xml with chapter references"""
        course_elem = ET.Element("course")
        course_elem.set("url_name", "2024-May")
        course_elem.set("org", "SoDiTEC")
        course_elem.set("course", "TDC01")
        
        for chapter_id in chapter_ids:
            chapter_elem = ET.SubElement(course_elem, "chapter")
            chapter_elem.set("url_name", chapter_id)
        
        course_xml = ET.tostring(course_elem, encoding='unicode')
        with open(os.path.join(course_dir, 'course.xml'), 'w', encoding='utf-8') as f:
            f.write(course_xml)
    
    def _create_chapter_xml(self, chapter_title: str, chapter_id: str) -> str:
        """Create chapter.xml file"""
        chapter_elem = ET.Element("chapter")
        chapter_elem.set("display_name", chapter_title)
        chapter_elem.set("url_name", chapter_id)
        return ET.tostring(chapter_elem, encoding='unicode')
    
    def _create_chapter_xml_with_references(self, chapter_title: str, sequential_ids: List[str]) -> str:
        """Create chapter.xml file with sequential references"""
        chapter_elem = ET.Element("chapter")
        chapter_elem.set("display_name", chapter_title)
        
        for seq_id in sequential_ids:
            seq_elem = ET.SubElement(chapter_elem, "sequential")
            seq_elem.set("url_name", seq_id)
        
        return ET.tostring(chapter_elem, encoding='unicode')
    
    def _create_sequential_xml(self, sequential_title: str, sequential_id: str) -> str:
        """Create sequential.xml file"""
        sequential_elem = ET.Element("sequential")
        sequential_elem.set("display_name", sequential_title)
        sequential_elem.set("url_name", sequential_id)
        return ET.tostring(sequential_elem, encoding='unicode')
    
    def _create_sequential_xml_with_references(self, sequential_title: str, vertical_ids: List[str]) -> str:
        """Create sequential.xml file with vertical references"""
        sequential_elem = ET.Element("sequential")
        sequential_elem.set("display_name", sequential_title)
        
        for vert_id in vertical_ids:
            vert_elem = ET.SubElement(sequential_elem, "vertical")
            vert_elem.set("url_name", vert_id)
        
        return ET.tostring(sequential_elem, encoding='unicode')
    
    def _sanitize_embed(self, code_or_url: str) -> str:
        """Sanitize embed code or wrap direct URL into a safe <iframe>.

        Handles:
        1. Plain URL:
           - Google Drive: extracts file ID and wraps with preview iframe (1200x640, allow="autoplay")
           - Other URLs: wraps into a safe responsive iframe
        2. HTML embed code:
           - Strips <script> tags and inline JS event handlers (onload, onerror, onclick, etc.)
           - Strips javascript: URLs
        """
        raw = (code_or_url or "").strip()
        if not raw:
            return '<p>Nội dung nhúng không tồn tại.</p>'

        # Case 1: Pure URL provided
        if raw.startswith(('http://', 'https://')) and '<' not in raw:
            # Check for Google Drive file link
            gdrive_match = re.search(r'drive\.google\.com/file/d/([a-zA-Z0-9_-]+)', raw)
            if gdrive_match:
                file_id = gdrive_match.group(1)
                preview_url = f"https://drive.google.com/file/d/{file_id}/preview"
                return f'<iframe src="{preview_url}" width="1200" height="640" allow="autoplay"></iframe>'

            # Default iframe for other URLs
            escaped_url = raw.replace('"', '&quot;')
            return f'<iframe src="{escaped_url}" width="100%" height="600px" frameborder="0" allowfullscreen></iframe>'

        # Case 2: HTML snippet (strip script tags and on* event handlers)
        sanitized = re.sub(r'<\s*script[^>]*>.*?<\s*/\s*script\s*>', '', raw, flags=re.IGNORECASE | re.DOTALL)
        sanitized = re.sub(r'<\s*style[^>]*>.*?<\s*/\s*style\s*>', '', sanitized, flags=re.IGNORECASE | re.DOTALL)
        sanitized = re.sub(r'\s+on[a-zA-Z]+\s*=\s*(?:"[^"]*"|\'[^\']*\'|[^\s>]+)', '', sanitized)
        sanitized = re.sub(r'(src|href)\s*=\s*["\']\s*javascript:[^"\']*["\']', '', sanitized, flags=re.IGNORECASE)

        return sanitized.strip()

    def _write_html_component(self, html_uuid: str, display_name: str, html_body: str, editor_raw: bool = False) -> None:
        """Write a pair of html/{uuid}.xml and html/{uuid}.html files.

        This matches the Open edX OLX standard where:
        - {uuid}.xml  – descriptor (metadata only, no inline content)
        - {uuid}.html – actual HTML content
        """
        html_dir = os.path.join(self.current_course_dir, 'html')
        os.makedirs(html_dir, exist_ok=True)

        # Descriptor XML
        if editor_raw:
            descriptor = f'<html filename="{html_uuid}" display_name="Raw HTML" editor="raw"/>'
        else:
            descriptor = f'<html filename="{html_uuid}"/>'
        with open(os.path.join(html_dir, f'{html_uuid}.xml'), 'w', encoding='utf-8') as f:
            f.write(descriptor)

        # Content HTML
        with open(os.path.join(html_dir, f'{html_uuid}.html'), 'w', encoding='utf-8') as f:
            f.write(html_body)

        self.logger.info(f"Created html component: {html_uuid}")

    def _create_vertical_xml(self, vertical_title: str, unit_data: Dict[str, Any], vertical_id: str) -> str:
        """Create vertical.xml file.

        The <vertical> tag carries only display_name (no url_name inline —
        the filename itself is the url_name, matching Studio OLX export).
        Child component tags are bare reference stubs: <html url_name="…"/>.
        All HTML content lives in separate html/{uuid}.xml + html/{uuid}.html files.
        """
        vertical_elem = ET.Element("vertical")
        vertical_elem.set("display_name", vertical_title)
        # NOTE: do NOT set url_name here — the filename is the url_name per OLX spec.

        if unit_data:
            unit_type = unit_data.get('type', 'text')

            if unit_type == 'video':
                # Reference to video XML file
                video_url_name = self._generate_uuid()
                video_elem = ET.SubElement(vertical_elem, "video")
                video_elem.set("url_name", video_url_name)
                self._create_video_xml(vertical_title, unit_data, video_url_name)

            elif unit_type == 'video_pdf':
                # Video reference
                video_url_name = self._generate_uuid()
                video_elem = ET.SubElement(vertical_elem, "video")
                video_elem.set("url_name", video_url_name)
                self._create_video_xml(vertical_title, unit_data, video_url_name)

                # HTML component for PDF (written to html/ directory)
                pdf_filename = unit_data.get('pdf_file', '')
                if pdf_filename:
                    html_uuid = self._generate_uuid()
                    html_elem = ET.SubElement(vertical_elem, "html")
                    html_elem.set("url_name", html_uuid)

                    pdf_html = (
                        '<div style="margin-top: 20px; padding: 15px; border: 1px solid #ddd; border-radius: 5px;">\n'
                        '    <h4>Tài liệu tham khảo</h4>\n'
                        f'    <p>Xem tài liệu PDF: <a href="/static/{pdf_filename}" target="_blank">{pdf_filename}</a></p>\n'
                        f'    <iframe src="/static/{pdf_filename}" width="100%" height="600px" style="border:none; margin-top: 10px;"></iframe>\n'
                        '</div>'
                    )
                    self._write_html_component(html_uuid, f"{vertical_title} - Tài liệu PDF", pdf_html)

            elif unit_type == 'pdf':
                # HTML component nhúng iframe PDF
                html_uuid = self._generate_uuid()
                html_elem = ET.SubElement(vertical_elem, "html")
                html_elem.set("url_name", html_uuid)

                pdf_filename = unit_data.get('file', '')
                if pdf_filename:
                    pdf_body = (
                        '<div style="margin-top: 20px; padding: 15px; border: 1px solid #ddd; border-radius: 5px;">\n'
                        '    <h4>Tài liệu tham khảo</h4>\n'
                        f'    <p>Xem tài liệu PDF: <a href="/static/{pdf_filename}" target="_blank">{pdf_filename}</a></p>\n'
                        f'    <iframe src="/static/{pdf_filename}" width="100%" height="600px" style="border:none; margin-top: 10px;"></iframe>\n'
                        '</div>'
                    )
                else:
                    pdf_body = '<p>PDF không tồn tại.</p>'
                self._write_html_component(html_uuid, vertical_title, pdf_body, editor_raw=True)

            elif unit_type == 'audio':
                # HTML component nhúng Audio (Raw HTML)
                html_uuid = self._generate_uuid()
                html_elem = ET.SubElement(vertical_elem, "html")
                html_elem.set("url_name", html_uuid)

                audio_filename = unit_data.get('audio_file') or unit_data.get('file', '')
                if audio_filename:
                    audio_body = (
                        f"<p>{vertical_title}</p>\n\n"
                        f"<audio controls>\n"
                        f'  <source src="/static/{audio_filename}" type="audio/mp3">\n'
                        f"</audio>"
                    )
                else:
                    audio_body = f"<p>{vertical_title}</p>\n<p>Audio không tồn tại.</p>"
                self._write_html_component(html_uuid, vertical_title, audio_body, editor_raw=True)

            elif unit_type in ['embed', 'raw_html', 'iframe']:
                # HTML component nhúng (Raw HTML: GDrive, SharePoint, Stream, etc.)
                html_uuid = self._generate_uuid()
                html_elem = ET.SubElement(vertical_elem, "html")
                html_elem.set("url_name", html_uuid)

                embed_code = unit_data.get('embed_code') or unit_data.get('content', '')
                embed_html = self._sanitize_embed(embed_code)
                self._write_html_component(html_uuid, vertical_title, embed_html, editor_raw=True)

            elif unit_type == 'docx':
                # DOCX: phần mềm không đọc được nội dung file DOCX hiện tại;
                # tạo placeholder HTML — nội dung sẽ được điền ở task sau.
                html_uuid = self._generate_uuid()
                html_elem = ET.SubElement(vertical_elem, "html")
                html_elem.set("url_name", html_uuid)
                self._write_html_component(html_uuid, vertical_title, '<p>(Nội dung DOCX)</p>')

            else:
                # Default: text/HTML trơn
                html_uuid = self._generate_uuid()
                text_elem = ET.SubElement(vertical_elem, "html")
                text_elem.set("url_name", html_uuid)
                html_body = unit_data.get('html_content', '') or '<p></p>'
                self._write_html_component(html_uuid, vertical_title, html_body)

        return ET.tostring(vertical_elem, encoding='unicode')
    
    def _create_video_xml(self, video_title: str, unit_data: Dict[str, Any], video_url_name: str):
        """Create video XML file in video directory"""
        video_elem = ET.Element("video")
        video_elem.set("url_name", video_url_name)
        video_elem.set("display_name", video_title)
        # Provide a stable edx_video_id
        video_elem.set("edx_video_id", self._generate_uuid())
        video_elem.set("youtube_id_1_0", "")
        video_elem.set("transcripts", "{}")
        
        # Add video URL if provided
        video_url = unit_data.get('video_url', '')
        if video_url:
            yt_id = self._extract_youtube_id(video_url)
            if yt_id:
                # Match the known-good format
                video_elem.set("youtube", f"1.00:{yt_id}")
                video_elem.set("youtube_id_1_0", yt_id)
                video_elem.set("html5_sources", "[]")
                # Add empty video_asset like the working sample
                ET.SubElement(video_elem, "video_asset", {
                    "client_video_id": "External Video",
                    "duration": "0.0",
                    "image": ""
                })
            else:
                # Non-YouTube: keep as html5_sources with <source>
                escaped_url = video_url.replace('"', '&quot;')
                video_elem.set("html5_sources", f'["{escaped_url}"]')
                source_elem = ET.SubElement(video_elem, "source")
                source_elem.set("src", video_url)
        
        # Convert to string and save to file
        video_xml = ET.tostring(video_elem, encoding='unicode')
        
        # Save to video directory
        video_dir = os.path.join(self.current_course_dir, 'video')
        os.makedirs(video_dir, exist_ok=True)
        video_file_path = os.path.join(video_dir, f'{video_url_name}.xml')
        
        with open(video_file_path, 'w', encoding='utf-8') as f:
            f.write(video_xml)
        
        self.logger.info(f"Created video XML file: {video_file_path}")

    def _extract_youtube_id(self, url: str) -> Optional[str]:
        """Extract YouTube video ID from various URL formats."""
        try:
            parsed = urlparse(url)
            host = (parsed.netloc or '').lower()
            if 'youtube.com' in host:
                # watch?v=ID
                qs = parse_qs(parsed.query)
                if 'v' in qs and qs['v']:
                    vid = qs['v'][0]
                    if re.fullmatch(r'[A-Za-z0-9_-]{11}', vid):
                        return vid
                # /embed/ID
                path_parts = [p for p in parsed.path.split('/') if p]
                if len(path_parts) >= 2 and path_parts[0] == 'embed':
                    vid = path_parts[1]
                    if re.fullmatch(r'[A-Za-z0-9_-]{11}', vid):
                        return vid
            if 'youtu.be' in host:
                # youtu.be/ID
                path_parts = [p for p in parsed.path.split('/') if p]
                if path_parts:
                    vid = path_parts[0]
                    if re.fullmatch(r'[A-Za-z0-9_-]{11}', vid):
                        return vid
            # Fallback regex
            m = re.search(r'(?:v=|be/|embed/)([A-Za-z0-9_-]{11})', url)
            if m:
                return m.group(1)
        except Exception:
            pass
        return None
    
    def _create_html_for_pdf(self, pdf_filename: str, vertical_id: str):
        """Create HTML file for PDF content"""
        html_content = f"""
        <div>
            <h3>PDF Content</h3>
            <p>PDF file: {pdf_filename}</p>
            <embed src="/static/{pdf_filename}" type="application/pdf" width="100%" height="600px" />
        </div>
        """
        
        # This would be implemented to create actual HTML files
        # For now, just log the intention
        self.logger.info(f"Would create HTML for PDF: {pdf_filename}")
    
    def _update_sequential_with_verticals(self, course_dir: str, sequential_id: str, vertical_ids: List[str]):
        """Update sequential.xml with vertical references"""
        sequential_path = os.path.join(course_dir, 'sequential', f'{sequential_id}.xml')
        
        tree = ET.parse(sequential_path)
        root = tree.getroot()
        
        for vertical_id in vertical_ids:
            vertical_elem = ET.SubElement(root, "vertical")
            vertical_elem.set("url_name", vertical_id)
        
        tree.write(sequential_path, encoding='utf-8', xml_declaration=True)
    
    def _update_chapter_with_sequentials(self, course_dir: str, chapter_id: str, sequential_ids: List[str]):
        """Update chapter.xml with sequential references"""
        chapter_path = os.path.join(course_dir, 'chapter', f'{chapter_id}.xml')
        
        tree = ET.parse(chapter_path)
        root = tree.getroot()
        
        for sequential_id in sequential_ids:
            sequential_elem = ET.SubElement(root, "sequential")
            sequential_elem.set("url_name", sequential_id)
        
        tree.write(chapter_path, encoding='utf-8', xml_declaration=True)
    
    def _create_problems_from_questions(self, questions: List[Dict[str, Any]], course_dir: str):
        """Create problem XML files from questions"""
        if questions:
            # Group questions into problem sets (e.g., 10 questions per problem)
            questions_per_problem = 10
            for i in range(0, len(questions), questions_per_problem):
                problem_id = self._generate_uuid()
                
                problem_questions = questions[i:i + questions_per_problem]
                problem_data = {"questions": problem_questions}
                
                problem_xml = self._create_problem_xml(problem_data)
                with open(os.path.join(course_dir, 'problem', f'{problem_id}.xml'), 'w', encoding='utf-8') as f:
                    f.write(problem_xml)
    
    def _create_problem_xml(self, question_data: Dict[str, Any]) -> str:
        """Create problem XML file with multiple choice questions"""
        problem_elem = ET.Element("problem")
        problem_elem.set("display_name", "Multiple Choice")
        
        # Add HTML structure for multiple choice
        html_content = "<p/>\n"
        html_content += '<h3 class="hd hd-2 problem-header">Câu hỏi</h3>\n'
        html_content += '<label>Chọn một đáp án đúng</label>\n'
        
        for i, question in enumerate(question_data.get("questions", [])):
            html_content += f'<p>{question["question"]}</p>\n'
            html_content += '<multiplechoiceresponse>\n'
            html_content += '    <choicegroup type="MultipleChoice" shuffle="true">\n'
            
            choices = question.get('choices', [])
            correct_answers = question.get('correct_answers', [])
            
            for j, choice in enumerate(choices):
                if j in correct_answers:
                    html_content += f'        <choice correct="true">{choice}</choice>\n'
                else:
                    html_content += f'        <choice correct="false">{choice}</choice>\n'
            
            html_content += '    </choicegroup>\n'
            html_content += '</multiplechoiceresponse>\n'
            html_content += '<p/>\n'
        
        # Add HTML content as text
        problem_elem.text = html_content
        
        return ET.tostring(problem_elem, encoding='unicode')
    
    # MIME type map for assets placed in course/static/
    _MIME_BY_EXT: Dict[str, str] = {
        '.pdf':  'application/pdf',
        '.mp3':  'audio/mpeg',
        '.mp4':  'video/mp4',
        '.ogg':  'audio/ogg',
        '.webm': 'video/webm',
        '.png':  'image/png',
        '.jpg':  'image/jpeg',
        '.jpeg': 'image/jpeg',
    }

    def _copy_pdfs_to_static(self, uploaded_pdfs: List[str], course_dir: str):
        """Copy uploaded asset files (PDF, MP3, …) to static directory.

        Renamed intent: handles any asset type, not just PDF.
        The old name is preserved to avoid breaking callers; actual logic
        now delegates to _copy_assets_to_static.
        """
        self._copy_assets_to_static(uploaded_pdfs, course_dir)

    def _copy_assets_to_static(self, asset_paths: List[str], course_dir: str):
        """Copy uploaded asset files to course/static/ directory."""
        static_dir = os.path.join(course_dir, "static")
        os.makedirs(static_dir, exist_ok=True)

        for asset_path in asset_paths:
            if os.path.exists(asset_path):
                filename = os.path.basename(asset_path)
                dest_path = os.path.join(static_dir, filename)
                shutil.copy2(asset_path, dest_path)
                self.logger.info(f"Copied asset to static: {filename}")

    def _create_assets_json(self, course_dir: str):
        """Create policies/assets.json from files actually present in course/static/.

        Generates the dict-map format that Open edX Studio exports, e.g.:
        {
          "slide.pdf": {
            "contentType": "application/pdf",
            "displayname": "slide.pdf",
            "filename": "asset-v1:{org}+{course}+{run}+type@asset+block@slide.pdf",
            "locked": false
          }
        }
        """
        import json

        static_dir = os.path.join(course_dir, 'static')
        policies_dir = os.path.join(course_dir, 'policies')
        os.makedirs(policies_dir, exist_ok=True)

        # Read org/course/run from course.xml if present; fall back to defaults.
        org, course_code, run = 'SoDiTEC', 'TDC01', '2024-May'
        course_xml_path = os.path.join(course_dir, 'course.xml')
        if os.path.exists(course_xml_path):
            try:
                root = ET.parse(course_xml_path).getroot()
                org = root.get('org', org)
                course_code = root.get('course', course_code)
                run = root.get('url_name', run)
            except Exception:
                pass

        assets_data: Dict[str, Any] = {}

        if os.path.isdir(static_dir):
            for fname in sorted(os.listdir(static_dir)):
                ext = os.path.splitext(fname)[1].lower()
                content_type = self._MIME_BY_EXT.get(ext, 'application/octet-stream')
                assets_data[fname] = {
                    'contentType': content_type,
                    'displayname': fname,
                    'filename': f'asset-v1:{org}+{course_code}+{run}+type@asset+block@{fname}',
                    'locked': False,
                }

        with open(os.path.join(policies_dir, 'assets.json'), 'w', encoding='utf-8') as f:
            json.dump(assets_data, f, ensure_ascii=False, indent=2)
    
    def _create_tarfile(self, source_dir: str, output_path: str):
        """Create tar.gz file from source directory"""
        parent_dir = os.path.dirname(output_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        with tarfile.open(output_path, "w:gz") as tar:
            for root, dirs, files in os.walk(source_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, source_dir)
                    tar.add(file_path, arcname=arcname) 