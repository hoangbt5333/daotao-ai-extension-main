"""
Shared helpers for export services
"""
import json
from lxml import etree
from typing import Dict, Any, Optional, List


def resolve_question_display_name(
    question_data: Dict[str, Any],
    index: int,
    used_names: Dict[str, int]
) -> str:
    """
    Determine a unique display_name for a question block in OpenEdX / Library OLX.

    Rules:
    1. If `name` (or `display_name`) is provided in `question_data` and is non-empty after trimming,
       use it as the base name.
    2. Otherwise, fall back to "Cau-NN" where NN is the 2-digit 1-based index (e.g. Cau-01, Cau-02, ...).
    3. If the base name has already been used within this export batch (`used_names`), append
       a suffix `_{count}` (e.g. `Cau-01_1`, `Cau-01_2`) without raising errors.
    4. The name is never extracted from choices or answer contents.
    
    Args:
        question_data: Dictionary containing question fields.
        index: 0-based question sequence index in the export batch.
        used_names: Mutable dictionary tracking occurrence counts of each base name.

    Returns:
        The final resolved display_name string.
    """
    raw_name = question_data.get("name")
    if raw_name is None:
        raw_name = question_data.get("display_name")

    if isinstance(raw_name, str) and raw_name.strip():
        base_name = raw_name.strip()
    else:
        base_name = f"Cau-{index + 1:02d}"

    # Handle duplicates in the same export batch
    if base_name not in used_names:
        used_names[base_name] = 1
        return base_name

    # Name is duplicate: generate suffix _1, _2, etc.
    count = used_names[base_name]
    used_names[base_name] = count + 1
    suffixed_name = f"{base_name}_{count}"
    
    # In the unlikely event suffixed_name was already claimed by an explicit name
    while suffixed_name in used_names:
        count += 1
        used_names[base_name] = count + 1
        suffixed_name = f"{base_name}_{count}"

    used_names[suffixed_name] = 1
    return suffixed_name


def create_markdown_content(question_data: Dict[str, Any]) -> str:
    """Create markdown content for problem according to Open edX format"""
    question_type = question_data.get("type", "multiple_choice")
    question_text = question_data.get("question", "")

    if question_type == "multiple_choice":
        markdown_content = f"<p/>\n{question_text}\n=====\n>>Chọn 1 đáp án đúng<<\n"
        choices = question_data.get('choices', [])
        correct_answers = question_data.get('correct_answers', [])
        fixed_choices = question_data.get('fixed_choices', [])

        for i, choice in enumerate(choices):
            is_correct = (i in correct_answers)
            is_fixed = (i in fixed_choices)

            if i == 0:
                # Dòng đầu tiên: Công tắc kích hoạt shuffle của Open edX
                if is_correct:
                    markdown_content += f"(!x) {choice}\n"
                else:
                    markdown_content += f"(!) {choice}\n"
            else:
                # Các dòng từ thứ 2 trở đi
                if is_fixed:
                    if is_correct:
                        markdown_content += f"(@x) {choice}\n"
                    else:
                        markdown_content += f"(@) {choice}\n"
                else:
                    if is_correct:
                        markdown_content += f"(x) {choice}\n"
                    else:
                        markdown_content += f"() {choice}\n"

    elif question_type == "multiple_select":
        markdown_content = f"<p/>\n{question_text}\n=====\n>>Chọn tất cả đáp án đúng<<\n"
        choices = question_data.get('choices', [])
        correct_answers = question_data.get('correct_answers', [])

        for i, choice in enumerate(choices):
            if i in correct_answers:
                markdown_content += f"[x] {choice}\n"
            else:
                markdown_content += f"[ ] {choice}\n"

    elif question_type == "text_input":
        markdown_content = f"<p/>\n{question_text}\n=====\n>>Nhập đáp án<<\n"
        markdown_content += f"= {question_data.get('correct_answer', '')}\n"

    elif question_type == "numerical":
        markdown_content = f"<p/>\n{question_text}\n=====\n>>Nhập số<<\n"
        markdown_content += f"= {question_data.get('correct_answer', '')}\n"

    else:
        markdown_content = f"<p/>\n{question_text}\n"

    return markdown_content


def build_single_problem_xml(
    question_data: Dict[str, Any],
    display_name: Optional[str] = None,
    partial_credit: Optional[str] = None
) -> etree.Element:
    """
    Build a single <problem> XML etree.Element for a question.
    Handles multiple_choice, multiple_select, text_input, and numerical.
    Strictly preserves <p/> and <label> tags.
    """
    tags_list = question_data.get('tags', [])
    if isinstance(tags_list, str):
        tags_list = [tags_list]

    tags_json = json.dumps([tag.replace('"', '\\"') for tag in tags_list], ensure_ascii=False)
    question_type = question_data.get("type", "multiple_choice")
    question_text = question_data.get("question", "")

    if display_name is None:
        display_name = resolve_question_display_name(question_data, 0, {})

    problem_elem = etree.Element("problem", display_name=display_name, tags=tags_json)

    # Markdown content attribute
    markdown_content = create_markdown_content(question_data)
    markdown_content = markdown_content.replace("\n", "&#10;")
    problem_elem.set("markdown", markdown_content)

    if question_type == "multiple_choice":
        mcr = etree.SubElement(problem_elem, "multiplechoiceresponse")
        etree.SubElement(mcr, "p")
        label = etree.SubElement(mcr, "label")
        label.text = "Chọn 1 đáp án đúng"
        p2 = etree.SubElement(mcr, "p")
        p2.text = question_text
        cg = etree.SubElement(mcr, "choicegroup", attrib={"type": "MultipleChoice", "shuffle": "true"})

        choices = question_data.get('choices', [])
        correct_answers = question_data.get('correct_answers', [])
        fixed_choices = question_data.get('fixed_choices', [])

        for i, choice in enumerate(choices):
            correct = "true" if i in correct_answers else "false"
            choice_attrib = {"correct": correct}
            if i in fixed_choices:
                choice_attrib["fixed"] = "true"
            c = etree.SubElement(cg, "choice", attrib=choice_attrib)
            c.text = choice

    elif question_type == "multiple_select":
        # Handle partial_credit: "halves" or "EDC"
        q_partial = question_data.get("partial_credit") or partial_credit
        cr_attrib = {}
        if q_partial in ["halves", "EDC"]:
            cr_attrib["partial_credit"] = q_partial

        cr = etree.SubElement(problem_elem, "choiceresponse", attrib=cr_attrib)
        etree.SubElement(cr, "p")
        label = etree.SubElement(cr, "label")
        label.text = "Chọn tất cả đáp án đúng"
        p2 = etree.SubElement(cr, "p")
        p2.text = question_text
        # Studio does not support shuffle on checkboxgroup - do not output shuffle attribute
        cbg = etree.SubElement(cr, "checkboxgroup")

        choices = question_data.get('choices', [])
        correct_answers = question_data.get('correct_answers', [])

        for i, choice in enumerate(choices):
            correct = "true" if i in correct_answers else "false"
            # Studio does not support fixed on checkbox choice - do not output fixed attribute
            c = etree.SubElement(cbg, "choice", attrib={"correct": correct})
            c.text = choice

    elif question_type in ["text_input", "numerical"]:
        sr = etree.SubElement(problem_elem, "stringresponse", attrib={"answer": str(question_data.get('correct_answer', ''))})
        etree.SubElement(sr, "p")
        label = etree.SubElement(sr, "label")
        label.text = "Nhập đáp án"
        p2 = etree.SubElement(sr, "p")
        p2.text = question_text
        etree.SubElement(sr, "textline", attrib={"size": "20"})

    return problem_elem
