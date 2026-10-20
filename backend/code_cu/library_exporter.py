import os
import uuid
import re
from lxml import etree
import json
from typing import List, Optional, Dict, Any

# --- Classes để parse và sinh XML ---
class Choice:
    def __init__(self, raw_text: str):
        self.text: str = raw_text
        self.is_correct: bool = False
        self.is_fixed: bool = False
        self.phan_tich()
    def phan_tich(self):
        if '(!x)' in self.text or '(x)' in self.text or '(x@)' in self.text:
            self.is_correct = True
        if '(@)' in self.text or '(x@)' in self.text:
            self.is_fixed = True
        self.text = re.sub(r'\((!x|x|!|x@|@|)\)', '', self.text).strip()
    def to_xml(self) -> etree.Element:
        attrs = {"correct": str(self.is_correct).lower()}
        if self.is_fixed:
            attrs["fixed"] = "true"
        c = etree.Element("choice", **attrs)
        c.text = escape_xml_text(self.text)
        return c

def escape_xml_text(text: str) -> str:
    text = text.replace('&', '&#38;')
    text = text.replace('"', '&#34;')
    text = text.replace('>', '&#62;')
    text = text.replace('<', '&#60;')
    return text

class Question:
    CHOICE_MARKERS = {'()', '(!)', '(x)', '(!x)', '(x@)', '(@)'}
    def __init__(self, text_block: str = '', choices=None, correct_answers=None, tags=None, question_type=None, image_url=None):
        self.full_markdown: str = text_block or ''
        self.prompt: str = ""
        self.image_html: Optional[str] = None
        self.choices: List[Choice] = []
        self.tags = tags or []
        self.question_type = question_type or "multiple_choice"
        self.image_url = image_url
        self.correct_answers = correct_answers if isinstance(correct_answers, list) else []
        if choices is not None and len(choices) > 0:
            # Luôn clean text_block để lấy câu hỏi gốc
            self.prompt = clean_question_text(text_block)
            self.choices = []
            for i, c in enumerate(choices):
                choice = Choice(c)
                if i in self.correct_answers:
                    choice.is_correct = True
                self.choices.append(choice)
        else:
            self.phan_tich_dong()
    def phan_tich_dong(self):
        import re
        lines = [l.strip() for l in self.full_markdown.split('\n') if l.strip()]
        # Loại bỏ các dòng chứa đáp án, ====, >>Chọn..., hoặc bắt đầu bằng (), (!x), [x], <img, img, Đáp án
        prompt_lines = []
        for l in lines:
            if l.startswith('p/'):
                l = l[2:].lstrip()
            if any([
                l.startswith('()'), l.startswith('(!x)'), l.startswith('[x]'), l.startswith('[ ]'),
                l.startswith('====='), '>>Chọn' in l, l.startswith('<img'), l.startswith('img '),
                l.startswith('Đáp án'), l.startswith('Đáp án:'),
                re.match(r'^[A-D]\.', l), re.match(r'^\d+\.', l),
            ]):
                continue
            prompt_lines.append(l)
            break  # chỉ lấy dòng đầu tiên hợp lệ
        self.prompt = ' '.join(prompt_lines).strip()
        # Lấy các dòng đáp án như cũ
        choice_lines = [l for l in lines if any(m in l for m in self.CHOICE_MARKERS)]
        self.choices = [Choice(line) for line in choice_lines]
    def to_xml(self, uuid: str, tags: List[str]) -> etree.Element:
        problem_elem = etree.Element("problem", display_name="Multiple Choice", tags=json.dumps(tags, ensure_ascii=False))
        # Markdown giữ nguyên logic cũ
        import html
        markdown_escaped = html.escape(self.full_markdown).replace('\n', '&#10;')
        problem_elem.set("markdown", markdown_escaped)
        mcr = etree.SubElement(problem_elem, "multiplechoiceresponse")
        etree.SubElement(mcr, "p")
        h3 = etree.SubElement(mcr, "h3", attrib={"class": "hd hd-2 problem-header"})
        h3.text = "Câu hỏi"
        label = etree.SubElement(mcr, "label")
        label.text = "Chọn 1 đáp án đúng"
        p2 = etree.SubElement(mcr, "p")
        # <p> chỉ lấy self.prompt (câu hỏi gốc), không escape, không ký hiệu
        p2.text = self.prompt
        if self.image_html:
            import re
            img_match = re.search(r'<img ([^>]+)>', self.image_html)
            if img_match:
                attrs = dict(re.findall(r'(\w+)="([^"]+)"', img_match.group(1)))
                etree.SubElement(mcr, "img", **attrs)
        elif self.image_url:
            etree.SubElement(mcr, "img", src=self.image_url)
        cg = etree.SubElement(mcr, "choicegroup", attrib={"type": "MultipleChoice", "shuffle": "true"})
        for choice in self.choices:
            cg.append(choice.to_xml())
        return problem_elem

# --- Pipeline export ---
def export_questions_to_library(questions: List['Question'], tags: List[str], output_dir: str, library_name: str, org: str = "SoDiTEC", library_code: str = "LIB001", start_time: str = '"2030-01-01T00:00:00Z"'):
    library_root = os.path.join(output_dir, 'library')
    os.makedirs(os.path.join(library_root, "problem"), exist_ok=True)
    os.makedirs(os.path.join(library_root, "policies"), exist_ok=True)
    uuids = []
    for q in questions:
        qid = uuid.uuid4().hex
        uuids.append(qid)
        xml_str = etree.tostring(q.to_xml(qid, tags), encoding='unicode', pretty_print=True, xml_declaration=False)
        fpath = os.path.join(library_root, "problem", f"{qid}.xml")
        print(f"[DEBUG] Ghi file: {fpath}")
        with open(fpath, "w", encoding="utf-8", newline='\n') as f:
            f.write(xml_str)
    library_xml = create_library_xml(library_name, org, library_code, problem_ids=uuids, start_time=start_time)
    fpath_lib = os.path.join(library_root, "library.xml")
    print(f"[DEBUG] Ghi file: {fpath_lib}")
    with open(fpath_lib, "w", encoding="utf-8", newline='\n') as f:
        f.write(library_xml)
    fpath_assets = os.path.join(library_root, "policies", "assets.json")
    print(f"[DEBUG] Ghi file: {fpath_assets}")
    with open(fpath_assets, "w", encoding="utf-8", newline='\n') as f:
        f.write('{}')
    print(f"Đã sinh thư viện Open edX tại {library_root}")

def generate_library_uuid():
    """Generate a unique ID for Library components"""
    return str(uuid.uuid4()).replace('-', '')

def create_library_xml(library_name: str, library_org: str = "SoDiTEC", library_code: str = "LIB001", problem_ids: list = None, start_time: str = '"2030-01-01T00:00:00Z"') -> str:
    """Create library.xml file for Open edX Library - mỗi thẻ namespace con có xmlns:nsX riêng, pretty-print"""
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
    # Add namespace children using {namespace-uri}name
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
    if problem_ids:
        for pid in problem_ids:
            etree.SubElement(library_elem, "problem", {"url_name": pid})
    # Pretty-print XML, lxml sẽ tự động sinh prefix ns0, ns1, ...
    xml_bytes = etree.tostring(library_elem, encoding='utf-8', pretty_print=True, xml_declaration=False)
    return xml_bytes.decode('utf-8')

def create_problem_xml_for_library(question_data: Dict[str, Any], tags: List[str] = None) -> str:
    """Create problem XML file for Library - XML chuẩn, pretty-print, self-closing tag đúng chuẩn, không có <?xml ...?>"""
    tags_list = tags or question_data.get('tags', [])
    if isinstance(tags_list, str):
        tags_list = [tags_list]
    tags_json = json.dumps([tag.replace('"', '\\"') for tag in tags_list], ensure_ascii=False)
    question_type = question_data.get("type", "multiple_choice")
    question_text = question_data.get("question", "")
    problem_elem = etree.Element("problem", display_name="Multiple Choice", tags=tags_json)
    # Markdown attribute
    if question_type == "multiple_choice":
        markdown_content = f"<p/>\n{question_text}\n=====\n>>Chọn 1 đáp án đúng<<\n"
        for i, choice in enumerate(question_data.get('choices', [])):
            if i in question_data.get('correct_answers', []):
                markdown_content += f"(!x) {choice}. \n"
            else:
                markdown_content += f"() {choice}\n"
    elif question_type == "multiple_select":
        markdown_content = f"<p/>\n{question_text}\n=====\n>>Chọn tất cả đáp án đúng<<\n"
        for i, choice in enumerate(question_data.get('choices', [])):
            if i in question_data.get('correct_answers', []):
                markdown_content += f"[x] {choice}\n"
            else:
                markdown_content += f"[ ] {choice}\n"
    elif question_type == "text_input":
        markdown_content = f"<p/>\n{question_text}\n=====\n>>Nhập đáp án<<\n"
        markdown_content += f"= {question_data.get('correct_answer', '')}\n"
    elif question_type == "numerical":
        markdown_content = f"<p/>\n{question_text}\n=====\n>>Nhập số<<\n"
        markdown_content += f"= {question_data.get('correct_answer', '')}\n"
    markdown_content = markdown_content.replace("\n", "&#10;")
    problem_elem.set("markdown", markdown_content)
    # Build XML thẻ con thực sự
    if question_type == "multiple_choice":
        mcr = etree.SubElement(problem_elem, "multiplechoiceresponse")
        etree.SubElement(mcr, "p")
        h3 = etree.SubElement(mcr, "h3", attrib={"class": "hd hd-2 problem-header"})
        h3.text = "Câu hỏi"
        label = etree.SubElement(mcr, "label")
        label.text = "Chọn 1 đáp án đúng"
        p2 = etree.SubElement(mcr, "p")
        p2.text = question_text
        cg = etree.SubElement(mcr, "choicegroup", attrib={"type": "MultipleChoice", "shuffle": "true"})
        for i, choice in enumerate(question_data.get('choices', [])):
            correct = "true" if i in question_data.get('correct_answers', []) else "false"
            c = etree.SubElement(cg, "choice", attrib={"correct": correct})
            c.text = choice
    elif question_type == "multiple_select":
        cr = etree.SubElement(problem_elem, "choiceresponse")
        etree.SubElement(cr, "p")
        h3 = etree.SubElement(cr, "h3", attrib={"class": "hd hd-2 problem-header"})
        h3.text = "Câu hỏi"
        label = etree.SubElement(cr, "label")
        label.text = "Chọn tất cả đáp án đúng"
        p2 = etree.SubElement(cr, "p")
        p2.text = question_text
        cbg = etree.SubElement(cr, "checkboxgroup")
        for i, choice in enumerate(question_data.get('choices', [])):
            correct = "true" if i in question_data.get('correct_answers', []) else "false"
            c = etree.SubElement(cbg, "choice", attrib={"correct": correct})
            c.text = choice
    elif question_type in ["text_input", "numerical"]:
        sr = etree.SubElement(problem_elem, "stringresponse", attrib={"answer": str(question_data.get('correct_answer', ''))})
        etree.SubElement(sr, "p")
        h3 = etree.SubElement(sr, "h3", attrib={"class": "hd hd-2 problem-header"})
        h3.text = "Câu hỏi"
        label = etree.SubElement(sr, "label")
        label.text = "Nhập đáp án"
        p2 = etree.SubElement(sr, "p")
        p2.text = question_text
        etree.SubElement(sr, "textline", attrib={"size": "20"})
    # Pretty-print XML, không có <?xml ...?>
    xml_bytes = etree.tostring(problem_elem, encoding='utf-8', pretty_print=True, xml_declaration=False)
    return xml_bytes.decode('utf-8')

def clean_question_text(text):
    import re
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    for l in lines:
        if l.startswith('p/'):
            l = l[2:].lstrip()
        if any([
            l.startswith('()'), l.startswith('(!x)'), l.startswith('[x]'), l.startswith('[ ]'),
            l.startswith('====='), '>>Chọn' in l, l.startswith('<img'), l.startswith('img '),
            l.startswith('Đáp án'), l.startswith('Đáp án:'),
            re.match(r'^[A-D]\.', l), re.match(r'^\d+\.', l),
        ]):
            continue
        return l
    return text.strip()

def export_library_to_tar(questions: List[dict], library_name: str, output_path: str, org: str = "SoDiTEC", library_code: str = "LIB001", start_time: str = '"2030-01-01T00:00:00Z"'):
    import tempfile
    import tarfile
    import shutil
    temp_dir = tempfile.mkdtemp()
    try:
        question_objs = []
        tags_list = []
        for q in questions:
            text_block = q.get('question', '')
            choices = q.get('choices', None)
            correct_answers = q.get('correct_answers', None)
            # Nếu không có correct_answers nhưng có answer, thì lấy answer
            if (not correct_answers or len(correct_answers) == 0) and 'answer' in q:
                correct_answers = q['answer']
            # Ép correct_answers thành mảng số
            if isinstance(correct_answers, list):
                correct_answers = [int(x) for x in correct_answers if isinstance(x, (int, float, str)) and str(x).isdigit()]
            else:
                correct_answers = []
            tags = q.get('tags', [])
            question_type = q.get('type', None)
            image_url = q.get('image_url', None)
            question_objs.append(Question(text_block, choices, correct_answers, tags, question_type, image_url))
            tags_list.append(tags)
        export_questions_to_library(question_objs, tags_list[0] if tags_list else [], temp_dir, library_name, org, library_code, start_time)
        library_root = os.path.join(temp_dir, 'library')
        print(f"[DEBUG] Nén thư mục: {library_root} -> {output_path}")
        with tarfile.open(output_path, "w:gz") as tar:
            tar.add(library_root, arcname='library')
        print(f"Library exported to: {output_path}")
        # Giải nén thử để kiểm tra cấu trúc
        import tempfile as tf
        check_dir = tf.mkdtemp()
        print(f"[DEBUG] Giải nén kiểm tra vào: {check_dir}")
        with tarfile.open(output_path, "r:gz") as tar:
            tar.extractall(check_dir)
        for root, dirs, files in os.walk(check_dir):
            level = root.replace(check_dir, '').count(os.sep)
            indent = '  ' * level
            print(f'{indent}{os.path.basename(root)}/')
            for f in files:
                print(f'{indent}  {f}')
        shutil.rmtree(check_dir)
        return True
    except Exception as e:
        print(f"Error exporting library: {e}")
        return False
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True) 