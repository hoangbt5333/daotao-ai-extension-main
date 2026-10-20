import os
import uuid
import xml.etree.ElementTree as ET
from typing import Dict, Any, List
import shutil

def generate_uuid():
    """Generate a unique ID for Open edX components"""
    return str(uuid.uuid4()).replace('-', '')

def create_course_xml(course_info: Dict[str, str] = None) -> str:
    """Create course.xml file"""
    if not course_info:
        course_info = {
            "url_name": "2024-May",
            "org": "SoDiTEC", 
            "course": "TDC01"
        }
    
    course_elem = ET.Element("course")
    course_elem.set("url_name", course_info["url_name"])
    course_elem.set("org", course_info["org"])
    course_elem.set("course", course_info["course"])
    
    return ET.tostring(course_elem, encoding='unicode')

def create_chapter_xml(chapter_title: str, sequential_ids: List[str]) -> str:
    """Create chapter XML file"""
    chapter_elem = ET.Element("chapter")
    chapter_elem.set("display_name", chapter_title)
    
    for seq_id in sequential_ids:
        seq_elem = ET.SubElement(chapter_elem, "sequential")
        seq_elem.set("url_name", seq_id)
    
    return ET.tostring(chapter_elem, encoding='unicode')

def create_sequential_xml(sequential_title: str, vertical_ids: List[str]) -> str:
    """Create sequential XML file"""
    sequential_elem = ET.Element("sequential")
    sequential_elem.set("display_name", sequential_title)
    
    for vert_id in vertical_ids:
        vert_elem = ET.SubElement(sequential_elem, "vertical")
        vert_elem.set("url_name", vert_id)
    
    return ET.tostring(sequential_elem, encoding='unicode')

def create_vertical_xml(vertical_title: str, unit_data: Dict[str, Any] = None, pdf_filename: str = None) -> str:
    """Create vertical XML file with support for different content types"""
    vertical_elem = ET.Element("vertical")
    vertical_elem.set("display_name", vertical_title)
    
    if unit_data:
        unit_type = unit_data.get('type', 'text')
        
        if unit_type == 'video':
            # Add video component
            video_elem = ET.SubElement(vertical_elem, "video")
            video_elem.set("display_name", vertical_title)
            video_elem.set("url_name", generate_uuid())
            
        elif unit_type == 'pdf':
            # Add HTML component nhúng iframe PDF
            html_elem = ET.SubElement(vertical_elem, "html")
            html_elem.set("display_name", vertical_title)
            html_elem.set("url_name", generate_uuid())
            if pdf_filename:
                # Nhúng iframe src="/static/filename.pdf"
                iframe_html = f'<iframe src="/static/{pdf_filename}" width="100%" height="600px" style="border:none;"></iframe>'
                html_elem.text = iframe_html
            else:
                html_elem.text = '<p>PDF không tồn tại.</p>'
        
        elif unit_type == 'docx':
            # Add document component
            doc_elem = ET.SubElement(vertical_elem, "html")
            doc_elem.set("display_name", vertical_title)
            doc_elem.set("url_name", generate_uuid())
            
        else:
            # Default text content
            text_elem = ET.SubElement(vertical_elem, "html")
            text_elem.set("display_name", vertical_title)
            text_elem.set("url_name", generate_uuid())
    
    return ET.tostring(vertical_elem, encoding='unicode')

def create_problem_xml(question_data: Dict[str, Any]) -> str:
    """Create problem XML file with multiple choice questions"""
    problem_elem = ET.Element("problem")
    problem_elem.set("display_name", "Multiple Choice")
    
    # Build markdown content
    markdown_content = "<p/>\n"
    
    for i, question in enumerate(question_data.get("questions", [])):
        markdown_content += f"Câu hỏi\n=====\n"
        markdown_content += f">>Chọn một đáp án đúng<<\n\n"
        markdown_content += f"{question['question']}\n"
        
        # Add choices
        for j, choice in enumerate(question['choices']):
            if j in question['answer']:
                markdown_content += f"(!x) {choice}\n"
            else:
                markdown_content += f"( ) {choice}\n"
        
        markdown_content += "\n\n"
    
    problem_elem.set("markdown", markdown_content)
    
    # Add HTML structure for multiple choice
    html_content = "<p/>\n"
    html_content += '<h3 class="hd hd-2 problem-header">Câu hỏi</h3>\n'
    html_content += '<label>Chọn một đáp án đúng</label>\n'
    
    for i, question in enumerate(question_data.get("questions", [])):
        html_content += f'<p>{question["question"]}</p>\n'
        html_content += '<multiplechoiceresponse>\n'
        html_content += '    <choicegroup type="MultipleChoice" shuffle="true">\n'
        
        for j, choice in enumerate(question['choices']):
            if j in question['answer']:
                html_content += f'        <choice correct="true">{choice}</choice>\n'
            else:
                html_content += f'        <choice correct="false">{choice}</choice>\n'
        
        html_content += '    </choicegroup>\n'
        html_content += '</multiplechoiceresponse>\n'
        html_content += '<p/>\n'
    
    # Add HTML content as text
    problem_elem.text = html_content
    
    return ET.tostring(problem_elem, encoding='unicode')

def create_directory_structure(base_path: str):
    """Create the standard Open edX directory structure"""
    directories = [
        "about",
        "policies", 
        "info",
        "static",
        "assets",
        "course",
        "chapter",
        "sequential", 
        "vertical",
        "problem",
        "html"
    ]
    
    for directory in directories:
        os.makedirs(os.path.join(base_path, directory), exist_ok=True)

PDF_SOURCE_DIR = r"D:/github/OUTSOURCE/daotao-ai-extension/course/static"

def export_openedx_structure(outline: List[Dict[str, Any]], questions: List[Dict[str, Any]], output_dir: str, pdf_source_dir: str = None, uploaded_pdfs: list = None):
    """
    Export outline and questions to Open edX format
    
    Args:
        outline: List of chapters with subsections and units
        questions: List of questions
        output_dir: Directory to create the course structure
        pdf_source_dir: Đường dẫn chứa file PDF gốc (tùy chọn)
        uploaded_pdfs: Danh sách file PDF upload từ người dùng (UploadFile)
    """
    
    # Create directory structure
    create_directory_structure(output_dir)
    
    pdf_target_dir = os.path.join(output_dir, "static")
    os.makedirs(pdf_target_dir, exist_ok=True)  # Luôn tạo static/
    print(f"[EXPORT] PDF target dir: {pdf_target_dir}")
    pdf_copied = False
    
    # Map tên file PDF upload
    uploaded_pdf_map = {}
    if uploaded_pdfs:
        for file in uploaded_pdfs:
            dst_pdf = os.path.join(pdf_target_dir, file.filename)
            with open(dst_pdf, "wb") as f:
                f.write(file.file.read())
            uploaded_pdf_map[file.filename] = dst_pdf
            print(f"[EXPORT] Saved uploaded PDF: {file.filename} -> {dst_pdf}")
            pdf_copied = True
    
    # Generate course.xml
    course_xml = create_course_xml()
    with open(os.path.join(output_dir, 'course.xml'), 'w', encoding='utf-8') as f:
        f.write(course_xml)
    
    # Process outline and create XML files
    chapter_ids = []
    sequential_ids = []
    vertical_ids = []
    problem_ids = []
    
    # Create chapters
    for chapter_idx, chapter in enumerate(outline):
        chapter_id = generate_uuid()
        chapter_ids.append(chapter_id)
        
        chapter_sequential_ids = []
        
        # Create subsections (sequentials)
        for subsection_idx, subsection in enumerate(chapter.get('subsections', [])):
            sequential_id = generate_uuid()
            chapter_sequential_ids.append(sequential_id)
            sequential_ids.append(sequential_id)
            
            sequential_vertical_ids = []
            
            # Create units (verticals)
            for unit_idx, unit in enumerate(subsection.get('units', [])):
                vertical_id = generate_uuid()
                sequential_vertical_ids.append(vertical_id)
                vertical_ids.append(vertical_id)
                
                # Nếu là PDF, đảm bảo file đã được upload
                pdf_filename = None
                if unit.get('type') == 'pdf' and unit.get('file'):
                    if unit['file'] in uploaded_pdf_map:
                        pdf_filename = unit['file']
                    else:
                        print(f"[EXPORT][WARNING] PDF {unit['file']} không được upload từ người dùng!")
                
                # Create vertical XML với pdf_filename
                vertical_xml = create_vertical_xml(unit.get('title', 'Untitled Unit'), unit, pdf_filename)
                with open(os.path.join(output_dir, 'vertical', f'{vertical_id}.xml'), 'w', encoding='utf-8') as f:
                    f.write(vertical_xml)
            
            # Create sequential XML
            sequential_xml = create_sequential_xml(subsection['title'], sequential_vertical_ids)
            with open(os.path.join(output_dir, 'sequential', f'{sequential_id}.xml'), 'w', encoding='utf-8') as f:
                f.write(sequential_xml)
        
        # Create chapter XML
        chapter_xml = create_chapter_xml(chapter['title'], chapter_sequential_ids)
        with open(os.path.join(output_dir, 'chapter', f'{chapter_id}.xml'), 'w', encoding='utf-8') as f:
            f.write(chapter_xml)
    
    # Nếu không có PDF nào được copy, tạo file .keep để static/ luôn xuất hiện
    if not pdf_copied:
        with open(os.path.join(pdf_target_dir, '.keep'), 'w') as f:
            f.write('')
        print(f"[EXPORT] No PDF copied, created .keep in static/")
    
    # Create problems from questions
    if questions:
        # Group questions into problem sets (e.g., 10 questions per problem)
        questions_per_problem = 10
        for i in range(0, len(questions), questions_per_problem):
            problem_id = generate_uuid()
            problem_ids.append(problem_id)
            
            problem_questions = questions[i:i + questions_per_problem]
            problem_data = {"questions": problem_questions}
            
            problem_xml = create_problem_xml(problem_data)
            with open(os.path.join(output_dir, 'problem', f'{problem_id}.xml'), 'w', encoding='utf-8') as f:
                f.write(problem_xml)
    
    # Create course.xml that references chapters
    course_elem = ET.Element("course")
    course_elem.set("url_name", "2024-May")
    course_elem.set("org", "SoDiTEC")
    course_elem.set("course", "TDC01")
    
    for chapter_id in chapter_ids:
        chapter_elem = ET.SubElement(course_elem, "chapter")
        chapter_elem.set("url_name", chapter_id)
    
    course_xml = ET.tostring(course_elem, encoding='unicode')
    with open(os.path.join(output_dir, 'course.xml'), 'w', encoding='utf-8') as f:
        f.write(course_xml)
    
    print(f"Open edX course structure created in: {output_dir}")
    print(f"Chapters: {len(chapter_ids)}")
    print(f"Sequentials: {len(sequential_ids)}")
    print(f"Verticals: {len(vertical_ids)}")
    print(f"Problems: {len(problem_ids)}") 