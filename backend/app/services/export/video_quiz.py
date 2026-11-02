"""
Video Quiz export service for OpenEdX
"""
import os
import json
import shutil
import tarfile
import tempfile
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional
from app.services.export.base import Exporter
from app.core.exceptions import ExportError
from app.services.export.video_quiz_helper import (
    generate_uuid,
    extract_youtube_id,
    parse_timestamp_to_seconds,
    build_invideoquiz_unit,
)


class VideoQuizExporter(Exporter):
    """Video Quiz export service for OpenEdX"""
    
    def __init__(self):
        super().__init__("video_quiz")
    
    def get_supported_formats(self) -> List[str]:
        return ["tar.gz"]
    
    def validate_data(self, data: Dict[str, Any]) -> bool:
        """Validate video quiz export data with specific user-friendly error messages."""
        required_keys = ["video_title", "video_url", "questions"]
        for key in required_keys:
            if key not in data or data[key] is None:
                raise ExportError(f"Dữ liệu export thiếu trường bắt buộc: '{key}'")
        
        video_title = str(data.get("video_title", "")).strip()
        if not video_title:
            raise ExportError("Tiêu đề video không được để trống.")
            
        video_url = str(data.get("video_url", "")).strip()
        yt_id = extract_youtube_id(video_url)
        if not yt_id:
            raise ExportError(
                "URL video không phải là YouTube hợp lệ (ID 11 ký tự). "
                "In-Video Quiz chỉ hỗ trợ video YouTube (không áp dụng với iframe/raw HTML theo mục 3.7 tài liệu hướng dẫn)."
            )
            
        questions = data.get("questions", [])
        if not isinstance(questions, list) or len(questions) == 0:
            raise ExportError("Vui lòng cung cấp ít nhất một câu hỏi cho video quiz.")
            
        seen_seconds = set()
        for idx, q in enumerate(questions):
            raw_ts = q.get("timestamp")
            if raw_ts is None:
                raw_ts = q.get("seconds")
            try:
                sec = parse_timestamp_to_seconds(raw_ts)
            except ValueError as e:
                raise ExportError(f"Câu hỏi {idx + 1}: {str(e)}")
                
            if sec in seen_seconds:
                ts_display = q.get("timestamp") or f"{sec}s"
                raise ExportError(
                    f"Phát hiện mốc thời gian bị trùng lặp: {sec} giây ({ts_display}). "
                    "Mỗi câu hỏi trong video phải có mốc thời gian xuất hiện riêng biệt, không được trùng lặp."
                )
            seen_seconds.add(sec)
        
        return True
    
    def export(self, data: Dict[str, Any], output_path: str) -> bool:
        """Export video quiz to OpenEdX format"""
        temp_dir = tempfile.mkdtemp()
        try:
            # Validate data first (raises ExportError if invalid)
            self.validate_data(data)
            
            # Extract data
            video_title = data.get("video_title", "Video Quiz")
            video_url = data.get("video_url", "")
            video_description = data.get("video_description", "")
            questions = data.get("questions", [])
            org = data.get("org", "SoDiTEC")
            course = data.get("course", "TDC01")
            run = data.get("run", "2024-May")
            
            # Create video quiz structure inside course/ wrapper
            self._create_video_quiz_structure(
                video_title=video_title,
                video_url=video_url,
                video_description=video_description,
                questions=questions,
                base_dir=temp_dir,
                org=org,
                course=course,
                run=run,
            )
            
            # Create tar.gz file
            self._create_tarfile(temp_dir, output_path)
            return True
            
        except ExportError:
            raise
        except Exception as e:
            self.logger.error(f"Error exporting video quiz: {e}")
            raise ExportError(f"Lỗi khi xuất video quiz: {str(e)}")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def _create_video_quiz_structure(
        self,
        video_title: str,
        video_url: str,
        video_description: str,
        questions: List[Dict[str, Any]],
        base_dir: str,
        org: str = "SoDiTEC",
        course: str = "TDC01",
        run: str = "2024-May",
    ):
        """Create standard OpenEdX course structure with course/ root wrapper."""
        # OpenEdX courses MUST be placed in a 'course/' directory inside the tarball
        course_dir = os.path.join(base_dir, "course")
        os.makedirs(course_dir, exist_ok=True)
        
        directories = [
            "about", "chapter", "sequential", "vertical",
            "problem", "video", "static", "policies", "course"
        ]
        for d in directories:
            os.makedirs(os.path.join(course_dir, d), exist_ok=True)
            
        # IDs for hierarchy
        chapter_id = generate_uuid()
        sequential_id = generate_uuid()
        vertical_id = generate_uuid()
        
        # 1. Use shared unit builder to generate video + problems + invideoquiz_v2
        build_invideoquiz_unit(
            course_dir=course_dir,
            unit_title=video_title,
            video_url=video_url,
            questions=questions,
            vertical_id=vertical_id,
            video_title=video_title,
        )
        
        # 2. course/course.xml (points to run)
        course_elem = ET.Element("course")
        course_elem.set("url_name", run)
        course_elem.set("org", org)
        course_elem.set("course", course)
        with open(os.path.join(course_dir, "course.xml"), "w", encoding="utf-8") as f:
            f.write(ET.tostring(course_elem, encoding="unicode"))
            
        # 3. course/course/{run}.xml (declares advanced_modules and chapter reference)
        run_elem = ET.Element("course")
        run_elem.set("advanced_modules", '["invideoquiz_v2"]')
        chap_ref = ET.SubElement(run_elem, "chapter")
        chap_ref.set("url_name", chapter_id)
        wiki_elem = ET.SubElement(run_elem, "wiki")
        wiki_elem.set("slug", f"{org}.{course}.{run}")
        with open(os.path.join(course_dir, "course", f"{run}.xml"), "w", encoding="utf-8") as f:
            f.write(ET.tostring(run_elem, encoding="unicode"))
            
        # 4. course/chapter/{chapter_id}.xml
        chap_elem = ET.Element("chapter")
        chap_elem.set("display_name", f"Chương {video_title}")
        seq_ref = ET.SubElement(chap_elem, "sequential")
        seq_ref.set("url_name", sequential_id)
        with open(os.path.join(course_dir, "chapter", f"{chapter_id}.xml"), "w", encoding="utf-8") as f:
            f.write(ET.tostring(chap_elem, encoding="unicode"))
            
        # 5. course/sequential/{sequential_id}.xml
        seq_elem = ET.Element("sequential")
        seq_elem.set("display_name", video_title)
        vert_ref = ET.SubElement(seq_elem, "vertical")
        vert_ref.set("url_name", vertical_id)
        with open(os.path.join(course_dir, "sequential", f"{sequential_id}.xml"), "w", encoding="utf-8") as f:
            f.write(ET.tostring(seq_elem, encoding="unicode"))
            
        # 6. course/policies/{run}/policy.json
        run_policy_dir = os.path.join(course_dir, "policies", run)
        os.makedirs(run_policy_dir, exist_ok=True)
        policy_data = {
            f"course/{run}": {
                "advanced_modules": ["invideoquiz_v2"]
            }
        }
        with open(os.path.join(run_policy_dir, "policy.json"), "w", encoding="utf-8") as f:
            json.dump(policy_data, f, ensure_ascii=False, indent=2)
            
        # 7. course/policies/assets.json
        with open(os.path.join(course_dir, "policies", "assets.json"), "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=2)
            
        # 8. course/static/.keep
        with open(os.path.join(course_dir, "static", ".keep"), "w", encoding="utf-8") as f:
            f.write("")
    
    def _create_tarfile(self, source_dir: str, output_path: str):
        """Create tar.gz file preserving course/ root directory."""
        parent_dir = os.path.dirname(output_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
            
        with tarfile.open(output_path, "w:gz") as tar:
            for root, dirs, files in os.walk(source_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, source_dir)
                    tar.add(file_path, arcname=arcname)
