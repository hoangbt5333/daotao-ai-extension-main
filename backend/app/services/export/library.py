"""
Library export service
"""
import os
import uuid
import tempfile
import tarfile
import shutil
import json
import re
from lxml import etree
from typing import Dict, Any, List, Optional
from app.services.export.base import Exporter
from app.services.export.helpers import resolve_question_display_name, build_single_problem_xml, create_markdown_content
from app.core.logging import get_logger


class LibraryExporter(Exporter):
    """Library export service for OpenEdX"""
    
    def __init__(self):
        super().__init__("library")
    
    def get_supported_formats(self) -> List[str]:
        return ["tar.gz"]
    
    def validate_data(self, data: Dict[str, Any]) -> bool:
        """Validate library export data"""
        required_keys = ["questions"]
        if not all(key in data for key in required_keys):
            return False
        
        questions = data.get("questions", [])
        if not isinstance(questions, list) or len(questions) == 0:
            return False

        for q in questions:
            if not isinstance(q, dict):
                return False
            q_type = q.get("type", "multiple_choice")
            choices = q.get("choices", [])
            correct = q.get("correct_answers", [])
            if q_type == "multiple_select":
                if len(choices) < 2 or len(correct) < 1:
                    return False
            elif q_type == "multiple_choice":
                if len(choices) < 2 or len(correct) != 1:
                    return False

        return True
    
    def export(self, data: Dict[str, Any], output_path: str) -> bool:
        """Export questions as Library format"""
        try:
            # Create temporary directory
            temp_dir = tempfile.mkdtemp()
            
            try:
                # Extract data
                questions = data.get("questions", [])
                library_name = data.get("library_name", "Question Library")
                org = data.get("org", "SoDiTEC")
                library_code = data.get("library_code", "LIB001")
                start_time = data.get("start_time", '"2030-01-01T00:00:00Z"')
                question_type = data.get("question_type", "multiple_choice")
                partial_credit = data.get("partial_credit", None)
                
                # Create library structure
                self._create_library_structure(questions, library_name, org, library_code, start_time, temp_dir, question_type, partial_credit=partial_credit)
                
                # Create tar.gz file
                self._create_tarfile(temp_dir, output_path)
                
                return True
                
            finally:
                # Clean up temporary directory
                shutil.rmtree(temp_dir, ignore_errors=True)
                
        except Exception as e:
            self.logger.error(f"Error exporting library: {e}")
            return False
    
    def _create_library_structure(self, questions: List[Dict[str, Any]], library_name: str, org: str, library_code: str, start_time: str, temp_dir: str, question_type: str = "multiple_choice", partial_credit: Optional[str] = None):
        """Create library structure"""
        # Create directories
        library_root = os.path.join(temp_dir, 'library')
        os.makedirs(os.path.join(library_root, "problem"), exist_ok=True)
        os.makedirs(os.path.join(library_root, "policies"), exist_ok=True)
        
        # Process questions and create problem files
        problem_ids = []
        used_names = {}
        for i, question_data in enumerate(questions):
            question_id = self._generate_uuid()
            problem_ids.append(question_id)
            
            # Nếu là multiple_select và chưa có type thì ép type
            if question_type == "multiple_select":
                question_data["type"] = "multiple_select"
            
            display_name = resolve_question_display_name(question_data, i, used_names)
            
            # Create problem XML
            problem_xml = self._create_problem_xml_for_library(question_data, display_name=display_name, partial_credit=partial_credit)
            
            with open(os.path.join(library_root, 'problem', f'{question_id}.xml'), 'w', encoding='utf-8') as f:
                f.write(problem_xml)
        
        # Create library.xml
        library_xml = self._create_library_xml(library_name, org, library_code, problem_ids, start_time)
        with open(os.path.join(library_root, 'library.xml'), 'w', encoding='utf-8') as f:
            f.write(library_xml)
        
        # Create policies/assets.json
        assets_json = {"assets": []}
        with open(os.path.join(library_root, 'policies', 'assets.json'), 'w', encoding='utf-8') as f:
            json.dump(assets_json, f, ensure_ascii=False, indent=2)
    
    def _generate_uuid(self) -> str:
        """Generate UUID for library components"""
        return str(uuid.uuid4()).replace('-', '')
    
    def _create_library_xml(self, library_name: str, library_org: str, library_code: str, problem_ids: List[str], start_time: str) -> str:
        """Create library.xml file"""
        NS = "http://code.edx.org/xblock/option"
        library_elem = etree.Element("library")
        library_elem.set("url_name", "library")
        library_elem.set("xblock-family", "xblock.v1")
        library_elem.set("tags", "[]")
        library_elem.set("display_name", library_name)
        library_elem.set("course_edit_method", "Studio")
        library_elem.set("days_early_for_beta", "null")
        library_elem.set("due", "null")
        library_elem.set("edxnotes", "false")
        library_elem.set("graceperiod", "null")
        library_elem.set("graded", "false")
        library_elem.set("group_access", "{}")
        library_elem.set("in_entrance_exam", "false")
        library_elem.set("max_attempts", "null")
        library_elem.set("rerandomize", "never")
        library_elem.set("self_paced", "false")
        library_elem.set("show_correctness", "always")
        library_elem.set("show_reset_button", "false")
        library_elem.set("showanswer", "finished")
        library_elem.set("start", start_time)
        library_elem.set("static_asset_path", "")
        library_elem.set("use_latex_compiler", "false")
        library_elem.set("user_partitions", "[]")
        library_elem.set("video_auto_advance", "false")
        library_elem.set("video_bumper", "{}")
        library_elem.set("video_speed_optimizations", "true")
        library_elem.set("visible_to_staff_only", "false")
        library_elem.set("hide_from_toc", "false")
        library_elem.set("chapters", "[]")
        library_elem.set("org", library_org)
        library_elem.set("library", library_code)
        
        # Add namespace children
        ns_names = [
            "name", "giturl", "matlab_api_key", "xqa_key", "chrome",
            "default_tab", "format", "source_file", "advanced_modules"
        ]
        
        for name in ns_names[:-1]:
            ns_elem = etree.SubElement(library_elem, f"{{{NS}}}{name}")
            ns_elem.set("none", "true")
        
        adv_elem = etree.SubElement(library_elem, f"{{{NS}}}advanced_modules")
        adv_elem.text = "[]"
        
        # Add problem references
        for problem_id in problem_ids:
            etree.SubElement(library_elem, "problem", {"url_name": problem_id})
        
        # Pretty-print XML
        xml_bytes = etree.tostring(library_elem, encoding='utf-8', pretty_print=True, xml_declaration=False)
        return xml_bytes.decode('utf-8')
    
    def _create_problem_xml_for_library(self, question_data: Dict[str, Any], display_name: Optional[str] = None, partial_credit: Optional[str] = None) -> str:
        """Create problem XML file for library"""
        elem = build_single_problem_xml(question_data, display_name=display_name, partial_credit=partial_credit)
        xml_bytes = etree.tostring(elem, encoding='utf-8', pretty_print=True, xml_declaration=False)
        return xml_bytes.decode('utf-8')

    def _create_markdown_content(self, question_data: Dict[str, Any]) -> str:
        """Create markdown content for problem"""
        return create_markdown_content(question_data)

    def _create_tarfile(self, source_dir: str, output_path: str):
        """Create tar.gz file from source directory"""
        with tarfile.open(output_path, "w:gz") as tar:
            tar.add(os.path.join(source_dir, 'library'), arcname='library') 