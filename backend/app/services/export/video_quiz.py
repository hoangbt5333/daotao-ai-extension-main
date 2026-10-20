"""
Video Quiz export service
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


class VideoQuizExporter(Exporter):
    """Video Quiz export service for OpenEdX"""
    
    def __init__(self):
        super().__init__("video_quiz")
    
    def get_supported_formats(self) -> List[str]:
        return ["tar.gz"]
    
    def validate_data(self, data: Dict[str, Any]) -> bool:
        """Validate video quiz export data"""
        required_keys = ["video_title", "video_url", "questions"]
        if not all(key in data for key in required_keys):
            return False
        
        questions = data.get("questions", [])
        if not isinstance(questions, list):
            return False
        
        return True
    
    def export(self, data: Dict[str, Any], output_path: str) -> bool:
        """Export video quiz to OpenEdX format"""
        try:
            # Create temporary directory
            temp_dir = tempfile.mkdtemp()
            
            try:
                # Extract data
                video_title = data.get("video_title", "Video Quiz")
                video_url = data.get("video_url", "")
                video_description = data.get("video_description", "")
                questions = data.get("questions", [])
                
                # Create video quiz structure
                self._create_video_quiz_structure(video_title, video_url, video_description, questions, temp_dir)
                
                # Create tar.gz file
                self._create_tarfile(temp_dir, output_path)
                
                return True
                
            finally:
                # Clean up temporary directory
                shutil.rmtree(temp_dir, ignore_errors=True)
                
        except Exception as e:
            self.logger.error(f"Error exporting video quiz: {e}")
            return False
    
    def _create_video_quiz_structure(self, video_title: str, video_url: str, video_description: str, questions: List[Dict[str, Any]], output_dir: str):
        """Create video quiz structure"""
        # Create directories
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(os.path.join(output_dir, "course"), exist_ok=True)
        os.makedirs(os.path.join(output_dir, "chapter"), exist_ok=True)
        os.makedirs(os.path.join(output_dir, "sequential"), exist_ok=True)
        os.makedirs(os.path.join(output_dir, "vertical"), exist_ok=True)
        os.makedirs(os.path.join(output_dir, "video"), exist_ok=True)
        os.makedirs(os.path.join(output_dir, "problem"), exist_ok=True)
        os.makedirs(os.path.join(output_dir, "static"), exist_ok=True)
        
        # Create course.xml
        course_xml = self._create_course_xml(video_title)
        with open(os.path.join(output_dir, 'course.xml'), 'w', encoding='utf-8') as f:
            f.write(course_xml)
        
        # Create chapter.xml
        chapter_xml = self._create_chapter_xml(f"Chương {video_title}")
        chapter_id = self._generate_uuid()
        with open(os.path.join(output_dir, 'chapter', f'{chapter_id}.xml'), 'w', encoding='utf-8') as f:
            f.write(chapter_xml)
        
        # Create sequential.xml
        sequential_xml = self._create_sequential_xml(video_title)
        sequential_id = self._generate_uuid()
        with open(os.path.join(output_dir, 'sequential', f'{sequential_id}.xml'), 'w', encoding='utf-8') as f:
            f.write(sequential_xml)
        
        # Create vertical.xml for video quiz
        vertical_id = self._generate_uuid()
        vertical_xml = self._create_vertical_xml_for_video_quiz(video_title, questions, vertical_id)
        with open(os.path.join(output_dir, 'vertical', f'{vertical_id}.xml'), 'w', encoding='utf-8') as f:
            f.write(vertical_xml)
        
        # Create video.xml
        video_id = self._generate_uuid()
        video_xml = self._create_video_xml(video_title, video_url, video_description, video_id)
        with open(os.path.join(output_dir, 'video', f'{video_id}.xml'), 'w', encoding='utf-8') as f:
            f.write(video_xml)
        
        # Create problem.xml for each question
        for i, question in enumerate(questions):
            question_id = question.get('id', self._generate_uuid())
            problem_xml = self._create_problem_xml_for_video_quiz(question, video_id)
            with open(os.path.join(output_dir, 'problem', f'{question_id}.xml'), 'w', encoding='utf-8') as f:
                f.write(problem_xml)
        
        # Create invideoquiz.xml
        invideoquiz_id = self._generate_uuid()
        invideoquiz_xml = self._create_invideoquiz_xml(questions, video_id, invideoquiz_id)
        with open(os.path.join(output_dir, 'problem', f'{invideoquiz_id}.xml'), 'w', encoding='utf-8') as f:
            f.write(invideoquiz_xml)
        
        # Add .keep file to static directory
        with open(os.path.join(output_dir, 'static', '.keep'), 'w') as f:
            f.write('')
    
    def _generate_uuid(self) -> str:
        """Generate UUID for video quiz components"""
        return str(uuid.uuid4()).replace('-', '')
    
    def _create_course_xml(self, course_name: str) -> str:
        """Create course.xml file"""
        course_elem = ET.Element("course")
        course_elem.set("org", "SoDiTEC")
        course_elem.set("course", "VIDEO001")
        course_elem.set("display_name", course_name)
        course_elem.set("url_name", course_name.lower().replace(" ", "_"))
        return ET.tostring(course_elem, encoding='unicode')
    
    def _create_chapter_xml(self, chapter_title: str) -> str:
        """Create chapter.xml file"""
        chapter_elem = ET.Element("chapter")
        chapter_elem.set("display_name", chapter_title)
        chapter_elem.set("url_name", chapter_title.lower().replace(" ", "_"))
        return ET.tostring(chapter_elem, encoding='unicode')
    
    def _create_sequential_xml(self, sequential_title: str) -> str:
        """Create sequential.xml file"""
        sequential_elem = ET.Element("sequential")
        sequential_elem.set("display_name", sequential_title)
        sequential_elem.set("url_name", sequential_title.lower().replace(" ", "_"))
        return ET.tostring(sequential_elem, encoding='unicode')
    
    def _create_vertical_xml_for_video_quiz(self, vertical_title: str, questions: List[Dict[str, Any]], vertical_id: str) -> str:
        """Create vertical.xml file for video quiz"""
        vertical_elem = ET.Element("vertical")
        vertical_elem.set("display_name", vertical_title)
        vertical_elem.set("url_name", vertical_id)
        
        # Add video reference
        video_elem = ET.SubElement(vertical_elem, "video")
        video_elem.set("url_name", f"video_{vertical_id}")
        
        # Add problem references for questions
        for question in questions:
            problem_elem = ET.SubElement(vertical_elem, "problem")
            problem_elem.set("url_name", question.get('id', self._generate_uuid()))
        
        # Add invideoquiz reference
        invideoquiz_elem = ET.SubElement(vertical_elem, "problem")
        invideoquiz_elem.set("url_name", f"invideoquiz_{vertical_id}")
        
        return ET.tostring(vertical_elem, encoding='unicode')
    
    def _create_video_xml(self, video_title: str, video_url: str, video_description: str, video_id: str) -> str:
        """Create video.xml file"""
        video_elem = ET.Element("video")
        video_elem.set("display_name", video_title)
        video_elem.set("url_name", video_id)
        
        # Add video attributes
        video_elem.set("youtube_id_1_0", video_url)
        video_elem.set("youtube_id_0_75", video_url)
        video_elem.set("youtube_id_1_25", video_url)
        video_elem.set("youtube_id_1_5", video_url)
        
        if video_description:
            video_elem.set("html5_sources", f'["{video_url}"]')
            video_elem.set("track", "")
            video_elem.set("download_video", "false")
            video_elem.set("sub", "")
            video_elem.set("start_time", "00:00:00")
            video_elem.set("end_time", "00:00:00")
            video_elem.set("show_captions", "true")
            video_elem.set("download_track", "false")
            video_elem.set("transcript_download_format", "srt")
            video_elem.set("transcript_language", "vi")
            video_elem.set("transcript_available_translations", "")
            video_elem.set("transcript_primary", "false")
            video_elem.set("transcript_indexing", "false")
            video_elem.set("transcript_source_language", "vi")
            video_elem.set("transcript_language_text", "Tiếng Việt")
            video_elem.set("transcript_source_language_text", "Tiếng Việt")
            video_elem.set("transcript_available_translations_text", "")
            video_elem.set("transcript_available_translations_json", "{}")
            video_elem.set("transcript_available_translations_json_text", "{}")
            video_elem.set("transcript_available_translations_json_text_1", "{}")
            video_elem.set("transcript_available_translations_json_text_2", "{}")
            video_elem.set("transcript_available_translations_json_text_3", "{}")
            video_elem.set("transcript_available_translations_json_text_4", "{}")
            video_elem.set("transcript_available_translations_json_text_5", "{}")
            video_elem.set("transcript_available_translations_json_text_6", "{}")
            video_elem.set("transcript_available_translations_json_text_7", "{}")
            video_elem.set("transcript_available_translations_json_text_8", "{}")
            video_elem.set("transcript_available_translations_json_text_9", "{}")
            video_elem.set("transcript_available_translations_json_text_10", "{}")
            video_elem.set("transcript_available_translations_json_text_11", "{}")
            video_elem.set("transcript_available_translations_json_text_12", "{}")
            video_elem.set("transcript_available_translations_json_text_13", "{}")
            video_elem.set("transcript_available_translations_json_text_14", "{}")
            video_elem.set("transcript_available_translations_json_text_15", "{}")
            video_elem.set("transcript_available_translations_json_text_16", "{}")
            video_elem.set("transcript_available_translations_json_text_17", "{}")
            video_elem.set("transcript_available_translations_json_text_18", "{}")
            video_elem.set("transcript_available_translations_json_text_19", "{}")
            video_elem.set("transcript_available_translations_json_text_20", "{}")
            video_elem.set("transcript_available_translations_json_text_21", "{}")
            video_elem.set("transcript_available_translations_json_text_22", "{}")
            video_elem.set("transcript_available_translations_json_text_23", "{}")
            video_elem.set("transcript_available_translations_json_text_24", "{}")
            video_elem.set("transcript_available_translations_json_text_25", "{}")
            video_elem.set("transcript_available_translations_json_text_26", "{}")
            video_elem.set("transcript_available_translations_json_text_27", "{}")
            video_elem.set("transcript_available_translations_json_text_28", "{}")
            video_elem.set("transcript_available_translations_json_text_29", "{}")
            video_elem.set("transcript_available_translations_json_text_30", "{}")
            video_elem.set("transcript_available_translations_json_text_31", "{}")
            video_elem.set("transcript_available_translations_json_text_32", "{}")
            video_elem.set("transcript_available_translations_json_text_33", "{}")
            video_elem.set("transcript_available_translations_json_text_34", "{}")
            video_elem.set("transcript_available_translations_json_text_35", "{}")
            video_elem.set("transcript_available_translations_json_text_36", "{}")
            video_elem.set("transcript_available_translations_json_text_37", "{}")
            video_elem.set("transcript_available_translations_json_text_38", "{}")
            video_elem.set("transcript_available_translations_json_text_39", "{}")
            video_elem.set("transcript_available_translations_json_text_40", "{}")
            video_elem.set("transcript_available_translations_json_text_41", "{}")
            video_elem.set("transcript_available_translations_json_text_42", "{}")
            video_elem.set("transcript_available_translations_json_text_43", "{}")
            video_elem.set("transcript_available_translations_json_text_44", "{}")
            video_elem.set("transcript_available_translations_json_text_45", "{}")
            video_elem.set("transcript_available_translations_json_text_46", "{}")
            video_elem.set("transcript_available_translations_json_text_47", "{}")
            video_elem.set("transcript_available_translations_json_text_48", "{}")
            video_elem.set("transcript_available_translations_json_text_49", "{}")
            video_elem.set("transcript_available_translations_json_text_50", "{}")
            video_elem.set("transcript_available_translations_json_text_51", "{}")
            video_elem.set("transcript_available_translations_json_text_52", "{}")
            video_elem.set("transcript_available_translations_json_text_53", "{}")
            video_elem.set("transcript_available_translations_json_text_54", "{}")
            video_elem.set("transcript_available_translations_json_text_55", "{}")
            video_elem.set("transcript_available_translations_json_text_56", "{}")
            video_elem.set("transcript_available_translations_json_text_57", "{}")
            video_elem.set("transcript_available_translations_json_text_58", "{}")
            video_elem.set("transcript_available_translations_json_text_59", "{}")
            video_elem.set("transcript_available_translations_json_text_60", "{}")
            video_elem.set("transcript_available_translations_json_text_61", "{}")
            video_elem.set("transcript_available_translations_json_text_62", "{}")
            video_elem.set("transcript_available_translations_json_text_63", "{}")
            video_elem.set("transcript_available_translations_json_text_64", "{}")
            video_elem.set("transcript_available_translations_json_text_65", "{}")
            video_elem.set("transcript_available_translations_json_text_66", "{}")
            video_elem.set("transcript_available_translations_json_text_67", "{}")
            video_elem.set("transcript_available_translations_json_text_68", "{}")
            video_elem.set("transcript_available_translations_json_text_69", "{}")
            video_elem.set("transcript_available_translations_json_text_70", "{}")
            video_elem.set("transcript_available_translations_json_text_71", "{}")
            video_elem.set("transcript_available_translations_json_text_72", "{}")
            video_elem.set("transcript_available_translations_json_text_73", "{}")
            video_elem.set("transcript_available_translations_json_text_74", "{}")
            video_elem.set("transcript_available_translations_json_text_75", "{}")
            video_elem.set("transcript_available_translations_json_text_76", "{}")
            video_elem.set("transcript_available_translations_json_text_77", "{}")
            video_elem.set("transcript_available_translations_json_text_78", "{}")
            video_elem.set("transcript_available_translations_json_text_79", "{}")
            video_elem.set("transcript_available_translations_json_text_80", "{}")
            video_elem.set("transcript_available_translations_json_text_81", "{}")
            video_elem.set("transcript_available_translations_json_text_82", "{}")
            video_elem.set("transcript_available_translations_json_text_83", "{}")
            video_elem.set("transcript_available_translations_json_text_84", "{}")
            video_elem.set("transcript_available_translations_json_text_85", "{}")
            video_elem.set("transcript_available_translations_json_text_86", "{}")
            video_elem.set("transcript_available_translations_json_text_87", "{}")
            video_elem.set("transcript_available_translations_json_text_88", "{}")
            video_elem.set("transcript_available_translations_json_text_89", "{}")
            video_elem.set("transcript_available_translations_json_text_90", "{}")
            video_elem.set("transcript_available_translations_json_text_91", "{}")
            video_elem.set("transcript_available_translations_json_text_92", "{}")
            video_elem.set("transcript_available_translations_json_text_93", "{}")
            video_elem.set("transcript_available_translations_json_text_94", "{}")
            video_elem.set("transcript_available_translations_json_text_95", "{}")
            video_elem.set("transcript_available_translations_json_text_96", "{}")
            video_elem.set("transcript_available_translations_json_text_97", "{}")
            video_elem.set("transcript_available_translations_json_text_98", "{}")
            video_elem.set("transcript_available_translations_json_text_99", "{}")
        
        return ET.tostring(video_elem, encoding='unicode')
    
    def _create_problem_xml_for_video_quiz(self, question_data: Dict[str, Any], video_id: str) -> str:
        """Create problem XML file for video quiz"""
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
    
    def _create_invideoquiz_xml(self, questions: List[Dict[str, Any]], video_id: str, invideoquiz_id: str) -> str:
        """Create invideoquiz.xml file"""
        invideoquiz_elem = ET.Element("problem")
        invideoquiz_elem.set("display_name", "Video Quiz")
        invideoquiz_elem.set("url_name", invideoquiz_id)
        
        # Add video quiz content
        html_content = f'<p>Video Quiz for video: {video_id}</p>\n'
        html_content += '<p>Questions will appear during video playback.</p>\n'
        
        # Add questions
        for i, question in enumerate(questions):
            html_content += f'<p><strong>Question {i+1}:</strong> {question.get("question", "")}</p>\n'
            choices = question.get('choices', [])
            for j, choice in enumerate(choices):
                html_content += f'<p>  {j+1}. {choice}</p>\n'
        
        invideoquiz_elem.text = html_content
        
        return ET.tostring(invideoquiz_elem, encoding='unicode')
    
    def _create_tarfile(self, source_dir: str, output_path: str):
        """Create tar.gz file from source directory"""
        with tarfile.open(output_path, "w:gz") as tar:
            for root, dirs, files in os.walk(source_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, source_dir)
                    tar.add(file_path, arcname=arcname) 