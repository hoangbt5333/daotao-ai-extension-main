import os
import uuid
import xml.etree.ElementTree as ET
from typing import Dict, Any, List
import json

def generate_exam_uuid():
    """Generate a unique ID for Exam components"""
    return str(uuid.uuid4()).replace('-', '')

def create_course_xml(course_name: str, course_org: str = "SoDiTEC", course_code: str = "EXAM001") -> str:
    """Create course.xml file for Open edX course"""
    course_elem = ET.Element("course")
    course_elem.set("org", course_org)
    course_elem.set("course", course_code)
    course_elem.set("display_name", course_name)
    course_elem.set("url_name", course_code.lower())
    return ET.tostring(course_elem, encoding='unicode')

def create_chapter_xml(chapter_title: str) -> str:
    """Create chapter.xml file for Open edX chapter"""
    chapter_elem = ET.Element("chapter")
    chapter_elem.set("display_name", chapter_title)
    chapter_elem.set("url_name", chapter_title.lower().replace(" ", "_"))
    return ET.tostring(chapter_elem, encoding='unicode')

def create_sequential_xml_for_exam(exam_name: str, exam_description: str = "", is_timed: bool = True, time_limit_minutes: int = 90) -> str:
    """Create sequential.xml file for Exam (Subsection)"""
    sequential_elem = ET.Element("sequential")
    sequential_elem.set("display_name", exam_name)
    sequential_elem.set("url_name", exam_name.lower().replace(" ", "_"))
    
    if exam_description:
        sequential_elem.set("description", exam_description)
    
    if is_timed:
        sequential_elem.set("is_timed_exam", "true")
        sequential_elem.set("time_limit_in_seconds", str(time_limit_minutes * 60))
    
    return ET.tostring(sequential_elem, encoding='unicode')

def create_vertical_xml_for_exam_section(section_title: str, questions: List[Dict[str, Any]]) -> str:
    """Create vertical.xml file for Exam section (Unit)"""
    vertical_elem = ET.Element("vertical")
    vertical_elem.set("display_name", section_title)
    vertical_elem.set("url_name", section_title.lower().replace(" ", "_"))
    
    # Add problem references
    for question in questions:
        problem_elem = ET.SubElement(vertical_elem, "problem")
        problem_elem.set("url_name", question.get('id', generate_exam_uuid()))
    
    return ET.tostring(vertical_elem, encoding='unicode')

def create_problem_xml_for_exam(question_data: Dict[str, Any]) -> str:
    """Create problem XML file for Exam with proper Open edX format"""
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

def create_exam_structure(exam_data: Dict[str, Any], output_dir: str):
    """Create Exam structure for Open edX import"""
    
    # Create directories
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(os.path.join(output_dir, "chapter"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "sequential"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "vertical"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "problem"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "static"), exist_ok=True)

    exam_name = exam_data.get("exam_name", "Đề thi")
    exam_description = exam_data.get("exam_description", "")
    is_timed = exam_data.get("is_timed", True)
    total_time = exam_data.get("total_time", 90)
    sections = exam_data.get("sections", [])

    # Create course.xml
    course_xml = create_course_xml(exam_name)
    with open(os.path.join(output_dir, 'course.xml'), 'w', encoding='utf-8') as f:
        f.write(course_xml)

    # Create chapter.xml
    chapter_xml = create_chapter_xml(f"Chương {exam_name}")
    with open(os.path.join(output_dir, 'chapter', f'{exam_name.lower().replace(" ", "_")}_chapter.xml'), 'w', encoding='utf-8') as f:
        f.write(chapter_xml)

    # Create sequential.xml (Exam subsection)
    sequential_xml = create_sequential_xml_for_exam(exam_name, exam_description, is_timed, total_time)
    with open(os.path.join(output_dir, 'sequential', f'{exam_name.lower().replace(" ", "_")}.xml'), 'w', encoding='utf-8') as f:
        f.write(sequential_xml)

    # Create vertical.xml for each section
    vertical_ids = []
    for i, section in enumerate(sections):
        section_title = section.get("title", f"Phần {i+1}")
        questions = section.get("questions", [])
        
        vertical_id = generate_exam_uuid()
        vertical_ids.append(vertical_id)
        
        vertical_xml = create_vertical_xml_for_exam_section(section_title, questions)
        with open(os.path.join(output_dir, 'vertical', f'{vertical_id}.xml'), 'w', encoding='utf-8') as f:
            f.write(vertical_xml)

        # Create problem.xml for each question
        for question in questions:
            question_id = question.get('id', generate_exam_uuid())
            problem_xml = create_problem_xml_for_exam(question)
            with open(os.path.join(output_dir, 'problem', f'{question_id}.xml'), 'w', encoding='utf-8') as f:
                f.write(problem_xml)

    # Add .keep file to static directory
    with open(os.path.join(output_dir, 'static', '.keep'), 'w') as f:
        f.write('')

    print(f"Exam structure created in: {output_dir}")
    print(f"Total sections: {len(sections)}")
    print(f"Total questions: {sum(len(s.get('questions', [])) for s in sections)}")

    return vertical_ids

def export_exam_to_tar(exam_data: Dict[str, Any], output_path: str):
    """Export exam as Open edX format to tar.gz file"""
    import tempfile
    import tarfile

    # Create temporary directory
    temp_dir = tempfile.mkdtemp()

    try:
        # Create exam structure
        create_exam_structure(exam_data, temp_dir)

        # Create tar.gz file
        with tarfile.open(output_path, "w:gz") as tar:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    tar.add(file_path, arcname=arcname)

        print(f"Exam exported to: {output_path}")
        return True

    except Exception as e:
        print(f"Error exporting exam: {e}")
        return False
    finally:
        # Clean up temporary directory
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True) 

def create_exam_subsection_structure(exam_data: Dict[str, Any], output_dir: str):
    """Create Exam subsection structure (sequential + vertical + problem) - KHÔNG có course.xml, chapter.xml"""
    
    # Create directories
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(os.path.join(output_dir, "sequential"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "vertical"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "problem"), exist_ok=True)

    exam_name = exam_data.get("exam_name", "Đề thi")
    exam_description = exam_data.get("exam_description", "")
    is_timed = exam_data.get("is_timed", True)
    total_time = exam_data.get("total_time", 90)
    sections = exam_data.get("sections", [])

    # Create sequential.xml (Exam subsection)
    sequential_xml = create_sequential_xml_for_exam(exam_name, exam_description, is_timed, total_time)
    with open(os.path.join(output_dir, 'sequential', f'{exam_name.lower().replace(" ", "_")}.xml'), 'w', encoding='utf-8') as f:
        f.write(sequential_xml)

    # Create vertical.xml for each section
    vertical_ids = []
    for i, section in enumerate(sections):
        section_title = section.get("title", f"Phần {i+1}")
        questions = section.get("questions", [])
        
        vertical_id = generate_exam_uuid()
        vertical_ids.append(vertical_id)
        
        vertical_xml = create_vertical_xml_for_exam_section(section_title, questions)
        with open(os.path.join(output_dir, 'vertical', f'{vertical_id}.xml'), 'w', encoding='utf-8') as f:
            f.write(vertical_xml)

        # Create problem.xml for each question
        for question in questions:
            question_id = question.get('id', generate_exam_uuid())
            problem_xml = create_problem_xml_for_exam(question)
            with open(os.path.join(output_dir, 'problem', f'{question_id}.xml'), 'w', encoding='utf-8') as f:
                f.write(problem_xml)

    print(f"Exam subsection structure created in: {output_dir}")
    print(f"Total sections: {len(sections)}")
    print(f"Total questions: {sum(len(s.get('questions', [])) for s in sections)}")

    return vertical_ids

def export_exam_as_subsection_only(exam_data: Dict[str, Any], output_path: str):
    """Export đề thi dạng subsection để thêm vào course có sẵn"""
    import tempfile
    import tarfile

    # Create temporary directory
    temp_dir = tempfile.mkdtemp()

    try:
        # Create exam subsection structure
        create_exam_subsection_structure(exam_data, temp_dir)

        # Create tar.gz file
        with tarfile.open(output_path, "w:gz") as tar:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    tar.add(file_path, arcname=arcname)

        print(f"Exam subsection exported to: {output_path}")
        return True

    except Exception as e:
        print(f"Error exporting exam subsection: {e}")
        return False
    finally:
        # Clean up temporary directory
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

def create_library_xml(library_name: str, library_org: str = "SoDiTEC", library_code: str = "LIB001") -> str:
    """Create library.xml file for Open edX library - phù hợp với cấu trúc mẫu"""
    library_elem = ET.Element("library")
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
    library_elem.set("org", library_org)
    library_elem.set("library", library_code)
    
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
    
    return ET.tostring(library_elem, encoding='unicode')

def export_exam_questions_as_library(sections: List[Dict], output_path: str):
    """Export câu hỏi từ đề thi dạng Library format - phù hợp với cấu trúc mẫu"""
    import tempfile
    import tarfile

    # Create temporary directory
    temp_dir = tempfile.mkdtemp()

    try:
        # Extract all questions from sections
        all_questions = []
        for section in sections:
            questions = section.get("questions", [])
            all_questions.extend(questions)

        # Create directories
        os.makedirs(os.path.join(temp_dir, "problem"), exist_ok=True)
        os.makedirs(os.path.join(temp_dir, "policies"), exist_ok=True)

        # Create problems first to get their IDs
        problem_ids = []
        for i, question in enumerate(all_questions):
            question_id = generate_exam_uuid()
            problem_ids.append(question_id)
            
            # Extract tags from question if available
            tags = question.get('tags', [])
            if isinstance(tags, str):
                tags = [tags]
            
            problem_xml = create_problem_xml_for_exam(question)
            with open(os.path.join(temp_dir, 'problem', f'{question_id}.xml'), 'w', encoding='utf-8') as f:
                f.write(problem_xml)

        # Create library.xml with problem references
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
        
        # Write library.xml
        library_xml = ET.tostring(library_elem, encoding='unicode')
        with open(os.path.join(temp_dir, 'library.xml'), 'w', encoding='utf-8') as f:
            f.write(library_xml)

        # Create policies/assets.json
        assets_json = {"assets": []}
        with open(os.path.join(temp_dir, 'policies', 'assets.json'), 'w', encoding='utf-8') as f:
            json.dump(assets_json, f, ensure_ascii=False, indent=2)

        # Create tar.gz file
        with tarfile.open(output_path, "w:gz") as tar:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    tar.add(file_path, arcname=arcname)

        print(f"Exam questions library exported to: {output_path}")
        return True

    except Exception as e:
        print(f"Error exporting exam questions library: {e}")
        return False
    finally:
        # Clean up temporary directory
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

def export_exam_section_only(section_data: Dict[str, Any], output_path: str):
    """Export chỉ một section của đề thi"""
    import tempfile
    import tarfile

    # Create temporary directory
    temp_dir = tempfile.mkdtemp()

    try:
        # Create directories
        os.makedirs(os.path.join(temp_dir, "vertical"), exist_ok=True)
        os.makedirs(os.path.join(temp_dir, "problem"), exist_ok=True)

        section_title = section_data.get("title", "Section")
        questions = section_data.get("questions", [])

        # Create vertical.xml for section
        vertical_id = generate_exam_uuid()
        vertical_xml = create_vertical_xml_for_exam_section(section_title, questions)
        with open(os.path.join(temp_dir, 'vertical', f'{vertical_id}.xml'), 'w', encoding='utf-8') as f:
            f.write(vertical_xml)

        # Create problem.xml for each question
        for question in questions:
            question_id = question.get('id', generate_exam_uuid())
            problem_xml = create_problem_xml_for_exam(question)
            with open(os.path.join(temp_dir, 'problem', f'{question_id}.xml'), 'w', encoding='utf-8') as f:
                f.write(problem_xml)

        # Create tar.gz file
        with tarfile.open(output_path, "w:gz") as tar:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    tar.add(file_path, arcname=arcname)

        print(f"Exam section exported to: {output_path}")
        return True

    except Exception as e:
        print(f"Error exporting exam section: {e}")
        return False
    finally:
        # Clean up temporary directory
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True) 