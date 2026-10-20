"""
Exam export service
"""
import os
import uuid
import tempfile
import tarfile
import shutil
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional
from app.services.export.base import Exporter
from app.core.logging import get_logger


class ExamExporter(Exporter):
    """Exam export service for OpenEdX"""
    
    def __init__(self):
        super().__init__("exam")
    
    def get_supported_formats(self) -> List[str]:
        return ["tar.gz"]
    
    def validate_data(self, data: Dict[str, Any]) -> bool:
        """Validate exam export data"""
        required_keys = ["exam_name", "sections"]
        if not all(key in data for key in required_keys):
            return False
        
        sections = data.get("sections", [])
        if not isinstance(sections, list) or len(sections) == 0:
            return False
        
        return True
    
    def export(self, data: Dict[str, Any], output_path: str) -> bool:
        """Export exam to OpenEdX format"""
        try:
            # Check export type
            export_type = data.get("export_type", "full")
            
            if export_type == "subsection":
                return self.export_subsection_only(data, output_path)
            elif export_type == "questions_library":
                sections = data.get("sections", [])
                return self.export_questions_as_library(sections, output_path)
            elif export_type == "section_only":
                section = data.get("section", {})
                return self.export_section_only(section, output_path)
            else:
                # Default: full exam export
                return self.export_full_exam(data, output_path)
                
        except Exception as e:
            self.logger.error(f"Error exporting exam: {e}")
            return False
    
    def export_subsection_only(self, data: Dict[str, Any], output_path: str) -> bool:
        """Export exam as subsection only (no course.xml, chapter.xml)"""
        try:
            temp_dir = tempfile.mkdtemp()
            
            try:
                exam_name = data.get("exam_name", "Đề thi")
                exam_description = data.get("exam_description", "")
                is_timed = data.get("is_timed", True)
                total_time = data.get("total_time", 90)
                sections = data.get("sections", [])
                
                # Create subsection structure only
                self._create_exam_subsection_structure(exam_name, exam_description, is_timed, total_time, sections, temp_dir)
                
                # Create tar.gz file
                self._create_tarfile(temp_dir, output_path)
                
                return True
                
            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)
                
        except Exception as e:
            self.logger.error(f"Error exporting exam subsection: {e}")
            return False
    
    def export_questions_as_library(self, sections: List[Dict[str, Any]], output_path: str) -> bool:
        """Export exam questions as library format"""
        try:
            temp_dir = tempfile.mkdtemp()
            
            try:
                # Extract all questions from sections
                all_questions = []
                for section in sections:
                    questions = section.get("questions", [])
                    all_questions.extend(questions)
                
                # Create library structure
                self._create_library_from_questions(all_questions, temp_dir)
                
                # Create tar.gz file
                self._create_tarfile(temp_dir, output_path)
                
                return True
                
            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)
                
        except Exception as e:
            self.logger.error(f"Error exporting exam questions library: {e}")
            return False
    
    def export_section_only(self, section_data: Dict[str, Any], output_path: str) -> bool:
        """Export only one section of exam"""
        try:
            temp_dir = tempfile.mkdtemp()
            
            try:
                section_title = section_data.get("title", "Section")
                questions = section_data.get("questions", [])
                
                # Create section structure
                self._create_section_structure(section_title, questions, temp_dir)
                
                # Create tar.gz file
                self._create_tarfile(temp_dir, output_path)
                
                return True
                
            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)
                
        except Exception as e:
            self.logger.error(f"Error exporting exam section: {e}")
            return False
    
    def export_full_exam(self, data: Dict[str, Any], output_path: str) -> bool:
        """Export full exam to OpenEdX format"""
        try:
            # Create temporary directory
            temp_dir = tempfile.mkdtemp()
            
            try:
                # Extract data
                exam_name = data.get("exam_name", "Đề thi")
                exam_description = data.get("exam_description", "")
                is_timed = data.get("is_timed", True)
                total_time = data.get("total_time", 90)
                sections = data.get("sections", [])
                
                # Create exam structure
                self._create_exam_structure(exam_name, exam_description, is_timed, total_time, sections, temp_dir)
                
                # Create tar.gz file
                self._create_tarfile(temp_dir, output_path)
                
                return True
                
            finally:
                # Clean up temporary directory
                shutil.rmtree(temp_dir, ignore_errors=True)
                
        except Exception as e:
            self.logger.error(f"Error exporting full exam: {e}")
            return False
    
    def _create_exam_structure(self, exam_name: str, exam_description: str, is_timed: bool, total_time: int, sections: List[Dict[str, Any]], output_dir: str):
        """Create complete exam structure"""
        # Create directories
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(os.path.join(output_dir, "chapter"), exist_ok=True)
        os.makedirs(os.path.join(output_dir, "sequential"), exist_ok=True)
        os.makedirs(os.path.join(output_dir, "vertical"), exist_ok=True)
        os.makedirs(os.path.join(output_dir, "problem"), exist_ok=True)
        os.makedirs(os.path.join(output_dir, "static"), exist_ok=True)
        
        # Create course.xml
        course_xml = self._create_course_xml(exam_name)
        with open(os.path.join(output_dir, 'course.xml'), 'w', encoding='utf-8') as f:
            f.write(course_xml)
        
        # Create chapter.xml
        chapter_xml = self._create_chapter_xml(f"Chương {exam_name}")
        chapter_id = self._generate_uuid()
        with open(os.path.join(output_dir, 'chapter', f'{chapter_id}.xml'), 'w', encoding='utf-8') as f:
            f.write(chapter_xml)
        
        # Create sequential.xml (Exam subsection)
        sequential_xml = self._create_sequential_xml_for_exam(exam_name, exam_description, is_timed, total_time)
        sequential_id = self._generate_uuid()
        with open(os.path.join(output_dir, 'sequential', f'{sequential_id}.xml'), 'w', encoding='utf-8') as f:
            f.write(sequential_xml)
        
        # Create vertical.xml for each section
        vertical_ids = []
        for i, section in enumerate(sections):
            section_title = section.get("title", f"Phần {i+1}")
            questions = section.get("questions", [])
            
            vertical_id = self._generate_uuid()
            vertical_ids.append(vertical_id)
            
            vertical_xml = self._create_vertical_xml_for_exam_section(section_title, questions)
            with open(os.path.join(output_dir, 'vertical', f'{vertical_id}.xml'), 'w', encoding='utf-8') as f:
                f.write(vertical_xml)
            
            # Create problem.xml for each question
            for question in questions:
                question_id = question.get('id', self._generate_uuid())
                problem_xml = self._create_problem_xml_for_exam(question)
                with open(os.path.join(output_dir, 'problem', f'{question_id}.xml'), 'w', encoding='utf-8') as f:
                    f.write(problem_xml)
        
        # Add .keep file to static directory
        with open(os.path.join(output_dir, 'static', '.keep'), 'w') as f:
            f.write('')
    
    def _create_exam_subsection_structure(self, exam_name: str, exam_description: str, is_timed: bool, total_time: int, sections: List[Dict[str, Any]], output_dir: str):
        """Create exam subsection structure (no course.xml, chapter.xml)"""
        # Create directories
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(os.path.join(output_dir, "sequential"), exist_ok=True)
        os.makedirs(os.path.join(output_dir, "vertical"), exist_ok=True)
        os.makedirs(os.path.join(output_dir, "problem"), exist_ok=True)
        
        # Create sequential.xml (Exam subsection)
        sequential_xml = self._create_sequential_xml_for_exam(exam_name, exam_description, is_timed, total_time)
        sequential_id = self._generate_uuid()
        with open(os.path.join(output_dir, 'sequential', f'{sequential_id}.xml'), 'w', encoding='utf-8') as f:
            f.write(sequential_xml)
        
        # Create vertical.xml for each section
        for i, section in enumerate(sections):
            section_title = section.get("title", f"Phần {i+1}")
            questions = section.get("questions", [])
            
            vertical_id = self._generate_uuid()
            
            vertical_xml = self._create_vertical_xml_for_exam_section(section_title, questions)
            with open(os.path.join(output_dir, 'vertical', f'{vertical_id}.xml'), 'w', encoding='utf-8') as f:
                f.write(vertical_xml)
            
            # Create problem.xml for each question
            for question in questions:
                question_id = question.get('id', self._generate_uuid())
                problem_xml = self._create_problem_xml_for_exam(question)
                with open(os.path.join(output_dir, 'problem', f'{question_id}.xml'), 'w', encoding='utf-8') as f:
                    f.write(problem_xml)
    
    def _create_library_from_questions(self, questions: List[Dict[str, Any]], output_dir: str):
        """Create library structure from questions"""
        # Create directories
        os.makedirs(os.path.join(output_dir, "problem"), exist_ok=True)
        os.makedirs(os.path.join(output_dir, "policies"), exist_ok=True)
        
        # Create problems first to get their IDs
        problem_ids = []
        for i, question in enumerate(questions):
            question_id = self._generate_uuid()
            problem_ids.append(question_id)
            
            problem_xml = self._create_problem_xml_for_exam(question)
            with open(os.path.join(output_dir, 'problem', f'{question_id}.xml'), 'w', encoding='utf-8') as f:
                f.write(problem_xml)
        
        # Create library.xml with problem references
        library_xml = self._create_library_xml(problem_ids)
        with open(os.path.join(output_dir, 'library.xml'), 'w', encoding='utf-8') as f:
            f.write(library_xml)
        
        # Create policies/assets.json
        assets_json = {"assets": []}
        import json
        with open(os.path.join(output_dir, 'policies', 'assets.json'), 'w', encoding='utf-8') as f:
            json.dump(assets_json, f, ensure_ascii=False, indent=2)
    
    def _create_section_structure(self, section_title: str, questions: List[Dict[str, Any]], output_dir: str):
        """Create section structure only"""
        # Create directories
        os.makedirs(os.path.join(output_dir, "vertical"), exist_ok=True)
        os.makedirs(os.path.join(output_dir, "problem"), exist_ok=True)
        
        # Create vertical.xml for section
        vertical_id = self._generate_uuid()
        vertical_xml = self._create_vertical_xml_for_exam_section(section_title, questions)
        with open(os.path.join(output_dir, 'vertical', f'{vertical_id}.xml'), 'w', encoding='utf-8') as f:
            f.write(vertical_xml)
        
        # Create problem.xml for each question
        for question in questions:
            question_id = question.get('id', self._generate_uuid())
            problem_xml = self._create_problem_xml_for_exam(question)
            with open(os.path.join(output_dir, 'problem', f'{question_id}.xml'), 'w', encoding='utf-8') as f:
                f.write(problem_xml)
    
    def _generate_uuid(self) -> str:
        """Generate UUID for exam components"""
        return str(uuid.uuid4()).replace('-', '')
    
    def _create_course_xml(self, course_name: str) -> str:
        """Create course.xml file"""
        course_elem = ET.Element("course")
        course_elem.set("org", "SoDiTEC")
        course_elem.set("course", "EXAM001")
        course_elem.set("display_name", course_name)
        course_elem.set("url_name", course_name.lower().replace(" ", "_"))
        return ET.tostring(course_elem, encoding='unicode')
    
    def _create_chapter_xml(self, chapter_title: str) -> str:
        """Create chapter.xml file"""
        chapter_elem = ET.Element("chapter")
        chapter_elem.set("display_name", chapter_title)
        chapter_elem.set("url_name", chapter_title.lower().replace(" ", "_"))
        return ET.tostring(chapter_elem, encoding='unicode')
    
    def _create_sequential_xml_for_exam(self, exam_name: str, exam_description: str, is_timed: bool, total_time: int) -> str:
        """Create sequential.xml file for exam"""
        sequential_elem = ET.Element("sequential")
        sequential_elem.set("display_name", exam_name)
        sequential_elem.set("url_name", exam_name.lower().replace(" ", "_"))
        
        if exam_description:
            sequential_elem.set("description", exam_description)
        
        if is_timed:
            sequential_elem.set("is_timed_exam", "true")
            sequential_elem.set("time_limit_in_seconds", str(total_time * 60))
        
        return ET.tostring(sequential_elem, encoding='unicode')
    
    def _create_vertical_xml_for_exam_section(self, section_title: str, questions: List[Dict[str, Any]]) -> str:
        """Create vertical.xml file for exam section"""
        vertical_elem = ET.Element("vertical")
        vertical_elem.set("display_name", section_title)
        vertical_elem.set("url_name", section_title.lower().replace(" ", "_"))
        
        # Add problem references
        for question in questions:
            problem_elem = ET.SubElement(vertical_elem, "problem")
            problem_elem.set("url_name", question.get('id', self._generate_uuid()))
        
        return ET.tostring(vertical_elem, encoding='unicode')
    
    def _create_problem_xml_for_exam(self, question_data: Dict[str, Any]) -> str:
        """Create problem XML file for exam"""
        problem_elem = ET.Element("problem")
        problem_elem.set("display_name", question_data.get("question", "Question")[:50] + "...")
        
        # Build HTML content based on question type
        question_type = question_data.get("type", "multiple_choice")
        html_content = f'<p>{question_data["question"]}</p>\n'
        
        if question_type == "multiple_choice":
            html_content += '<multiplechoiceresponse>\n'
            html_content += '    <choicegroup type="MultipleChoice" shuffle="true">\n'
            for i, choice in enumerate(question_data.get('choices', [])):
                if i in question_data.get('correct_answers', []):
                    html_content += f'        <choice correct="true">{choice}</choice>\n'
                else:
                    html_content += f'        <choice correct="false">{choice}</choice>\n'
            html_content += '    </choicegroup>\n'
            html_content += '</multiplechoiceresponse>\n'
        
        elif question_type == "multiple_select":
            html_content += '<choiceresponse>\n'
            html_content += '    <checkboxgroup>\n'
            for i, choice in enumerate(question_data.get('choices', [])):
                if i in question_data.get('correct_answers', []):
                    html_content += f'        <choice correct="true">{choice}</choice>\n'
                else:
                    html_content += f'        <choice correct="false">{choice}</choice>\n'
            html_content += '    </checkboxgroup>\n'
            html_content += '</choiceresponse>\n'
        
        elif question_type in ["text_input", "numerical"]:
            html_content += '<stringresponse answer="' + str(question_data.get('correct_answer', '')) + '">\n'
            html_content += '    <textline size="20"/>\n'
            html_content += '</stringresponse>\n'
        
        # Set content
        problem_elem.text = html_content
        
        return ET.tostring(problem_elem, encoding='unicode')
    
    def _create_library_xml(self, problem_ids: List[str]) -> str:
        """Create library.xml file"""
        library_elem = ET.Element("library")
        library_elem.set("url_name", "library")
        library_elem.set("xblock-family", "xblock.v1")
        library_elem.set("tags", "[]")
        library_elem.set("display_name", "Exam Questions Library")
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
        library_elem.set("start", "&quot;2030-01-01T00:00:00Z&quot;")
        library_elem.set("static_asset_path", "")
        library_elem.set("use_latex_compiler", "false")
        library_elem.set("user_partitions", "[]")
        library_elem.set("video_auto_advance", "false")
        library_elem.set("video_bumper", "{}")
        library_elem.set("video_speed_optimizations", "true")
        library_elem.set("visible_to_staff_only", "false")
        library_elem.set("hide_from_toc", "false")
        library_elem.set("chapters", "[]")
        library_elem.set("org", "SoDiTEC")
        library_elem.set("library", "EXAM_LIB")
        
        # Add required namespace elements
        namespaces = [
            ("ns0", "name", "http://code.edx.org/xblock/option"),
            ("ns1", "giturl", "http://code.edx.org/xblock/option"),
            ("ns2", "matlab_api_key", "http://code.edx.org/xblock/option"),
            ("ns3", "xqa_key", "http://code.edx.org/xblock/option"),
            ("ns4", "chrome", "http://code.edx.org/xblock/option"),
            ("ns5", "default_tab", "http://code.edx.org/xblock/option"),
            ("ns6", "format", "http://code.edx.org/xblock/option"),
            ("ns7", "source_file", "http://code.edx.org/xblock/option"),
            ("ns8", "advanced_modules", "http://code.edx.org/xblock/option")
        ]
        
        for prefix, name, namespace in namespaces:
            ns_elem = ET.SubElement(library_elem, f"{{{namespace}}}{name}")
            ns_elem.set("none", "true")
        
        # Add advanced_modules with content
        advanced_modules_elem = library_elem.find(".//{http://code.edx.org/xblock/option}advanced_modules")
        if advanced_modules_elem is not None:
            advanced_modules_elem.text = "[]"
        
        # Add problem references
        for problem_id in problem_ids:
            problem_elem = ET.SubElement(library_elem, "problem")
            problem_elem.set("url_name", problem_id)
        
        return ET.tostring(library_elem, encoding='unicode')
    
    def _create_tarfile(self, source_dir: str, output_path: str):
        """Create tar.gz file from source directory"""
        with tarfile.open(output_path, "w:gz") as tar:
            for root, dirs, files in os.walk(source_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, source_dir)
                    tar.add(file_path, arcname=arcname) 