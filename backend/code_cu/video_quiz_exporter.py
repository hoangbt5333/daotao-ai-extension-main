import os
import uuid
import xml.etree.ElementTree as ET
from typing import Dict, Any, List
import json

def generate_video_quiz_uuid():
    """Generate a unique ID for Video Quiz components"""
    return str(uuid.uuid4()).replace('-', '')

def create_course_xml(course_name: str, course_org: str = "SoDiTEC", course_code: str = "VIDEO001") -> str:
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

def create_sequential_xml(sequential_title: str) -> str:
    """Create sequential.xml file for Open edX sequential"""
    sequential_elem = ET.Element("sequential")
    sequential_elem.set("display_name", sequential_title)
    sequential_elem.set("url_name", sequential_title.lower().replace(" ", "_"))
    return ET.tostring(sequential_elem, encoding='unicode')

def create_vertical_xml_for_video_quiz(video_title: str, video_url: str, questions: List[Dict[str, Any]]) -> str:
    """Create vertical.xml file for Video Quiz (Unit)"""
    vertical_elem = ET.Element("vertical")
    vertical_elem.set("display_name", video_title)
    vertical_elem.set("url_name", video_title.lower().replace(" ", "_"))
    
    # Generate IDs
    video_id = generate_video_quiz_uuid()
    quiz_controller_id = generate_video_quiz_uuid()
    
    # Add video block
    video_elem = ET.SubElement(vertical_elem, "video")
    video_elem.set("url_name", video_id)
    video_elem.set("display_name", video_title)
    
    # Add problem blocks for each question
    problem_ids = []
    for question in questions:
        problem_id = question.get('id', generate_video_quiz_uuid())
        problem_ids.append(problem_id)
        
        problem_elem = ET.SubElement(vertical_elem, "problem")
        problem_elem.set("url_name", problem_id)
        problem_elem.set("display_name", f"Câu hỏi {question.get('timestamp', '00:00')}")
    
    # Add in-video quiz controller
    quiz_elem = ET.SubElement(vertical_elem, "invideoquiz")
    quiz_elem.set("url_name", quiz_controller_id)
    
    # Create timemap JSON
    timemap = {
        "video_location": video_id,
        "problem_timemap": {}
    }
    
    for question in questions:
        seconds = question.get('seconds', 0)
        problem_id = question.get('id', generate_video_quiz_uuid())
        timemap["problem_timemap"][str(seconds)] = problem_id
    
    quiz_elem.text = json.dumps(timemap, indent=2)
    
    return ET.tostring(vertical_elem, encoding='unicode')

def create_video_xml(video_title: str, video_url: str, video_description: str = "") -> str:
    """Create video.xml file for video block"""
    video_elem = ET.Element("video")
    video_elem.set("display_name", video_title)
    video_elem.set("url_name", video_title.lower().replace(" ", "_"))
    
    if video_description:
        video_elem.set("description", video_description)
    
    # Add video source
    source_elem = ET.SubElement(video_elem, "source")
    source_elem.text = video_url
    
    return ET.tostring(video_elem, encoding='unicode')

def create_problem_xml_for_video_quiz(question_data: Dict[str, Any]) -> str:
    """Create problem XML file for Video Quiz with proper Open edX format"""
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

def create_invideoquiz_xml(timemap_data: Dict[str, Any]) -> str:
    """Create invideoquiz.xml file for quiz controller"""
    quiz_elem = ET.Element("invideoquiz")
    quiz_elem.text = json.dumps(timemap_data, indent=2)
    return ET.tostring(quiz_elem, encoding='unicode')

def create_video_quiz_structure(video_quiz_data: Dict[str, Any], output_dir: str):
    """Create Video Quiz structure for Open edX import"""
    
    # Create directories
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(os.path.join(output_dir, "chapter"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "sequential"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "vertical"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "video"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "problem"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "invideoquiz"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "static"), exist_ok=True)

    video_title = video_quiz_data.get("video_title", "Video Quiz")
    video_url = video_quiz_data.get("video_url", "")
    video_description = video_quiz_data.get("video_description", "")
    questions = video_quiz_data.get("questions", [])

    # Generate IDs
    video_id = generate_video_quiz_uuid()
    quiz_controller_id = generate_video_quiz_uuid()
    vertical_id = generate_video_quiz_uuid()

    # Create course.xml
    course_xml = create_course_xml(video_title)
    with open(os.path.join(output_dir, 'course.xml'), 'w', encoding='utf-8') as f:
        f.write(course_xml)

    # Create chapter.xml
    chapter_xml = create_chapter_xml(f"Chương {video_title}")
    with open(os.path.join(output_dir, 'chapter', f'{video_title.lower().replace(" ", "_")}_chapter.xml'), 'w', encoding='utf-8') as f:
        f.write(chapter_xml)

    # Create sequential.xml
    sequential_xml = create_sequential_xml(f"Bài {video_title}")
    with open(os.path.join(output_dir, 'sequential', f'{video_title.lower().replace(" ", "_")}_sequential.xml'), 'w', encoding='utf-8') as f:
        f.write(sequential_xml)

    # Create vertical.xml (main unit)
    vertical_xml = create_vertical_xml_for_video_quiz(video_title, video_url, questions)
    with open(os.path.join(output_dir, 'vertical', f'{vertical_id}.xml'), 'w', encoding='utf-8') as f:
        f.write(vertical_xml)

    # Create video.xml
    video_xml = create_video_xml(video_title, video_url, video_description)
    with open(os.path.join(output_dir, 'video', f'{video_id}.xml'), 'w', encoding='utf-8') as f:
        f.write(video_xml)

    # Create problem.xml for each question
    timemap = {
        "video_location": video_id,
        "problem_timemap": {}
    }
    
    for question in questions:
        question_id = question.get('id', generate_video_quiz_uuid())
        seconds = question.get('seconds', 0)
        
        problem_xml = create_problem_xml_for_video_quiz(question)
        with open(os.path.join(output_dir, 'problem', f'{question_id}.xml'), 'w', encoding='utf-8') as f:
            f.write(problem_xml)
        
        timemap["problem_timemap"][str(seconds)] = question_id

    # Create invideoquiz.xml (controller)
    quiz_xml = create_invideoquiz_xml(timemap)
    with open(os.path.join(output_dir, 'invideoquiz', f'{quiz_controller_id}.xml'), 'w', encoding='utf-8') as f:
        f.write(quiz_xml)

    # Add .keep file to static directory
    with open(os.path.join(output_dir, 'static', '.keep'), 'w') as f:
        f.write('')

    print(f"Video Quiz structure created in: {output_dir}")
    print(f"Video ID: {video_id}")
    print(f"Total questions: {len(questions)}")
    print(f"Timemap: {timemap}")

    return {
        "vertical_id": vertical_id,
        "video_id": video_id,
        "quiz_controller_id": quiz_controller_id,
        "timemap": timemap
    }

def export_video_quiz_to_tar(video_quiz_data: Dict[str, Any], output_path: str):
    """Export video quiz as Open edX format to tar.gz file"""
    import tempfile
    import tarfile

    # Create temporary directory
    temp_dir = tempfile.mkdtemp()

    try:
        # Create video quiz structure
        create_video_quiz_structure(video_quiz_data, temp_dir)

        # Create tar.gz file
        with tarfile.open(output_path, "w:gz") as tar:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    tar.add(file_path, arcname=arcname)

        print(f"Video Quiz exported to: {output_path}")
        return True

    except Exception as e:
        print(f"Error exporting video quiz: {e}")
        return False
    finally:
        # Clean up temporary directory
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True) 