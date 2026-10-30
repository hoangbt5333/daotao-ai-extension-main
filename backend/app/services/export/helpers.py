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
    """
    Create markdown content for problem according to Open edX Studio Simple Editor plain format.
    Plain format (matches library.mau_chuan.tar.gz reference):
    - No >>...<<, no =====, no <p/>, no ||
    - First line: question text (if present)
    - multiple_choice:
      - Line 0: (!x) or (!) ONLY when question has shuffle; otherwise (x) or ( )
      - Subsequent lines: (@x) or (@) when fixed; otherwise (x) or ( )
      - Wrong choice marker is strictly "( )" with space (never "()")
    - multiple_select:
      - [x] and [ ]; never ! or @
    - text_input / numerical:
      - = {correct_answer}
    """
    question_type = question_data.get("type", "multiple_choice")
    question_text = (question_data.get("question") or "").strip()

    markdown_content = f"{question_text}\n" if question_text else ""

    if question_type == "multiple_choice":
        choices = question_data.get('choices', [])
        correct_answers = question_data.get('correct_answers', [])
        fixed_choices = question_data.get('fixed_choices', [])
        has_shuffle = bool(question_data.get('shuffle', False))

        for i, choice in enumerate(choices):
            is_correct = (i in correct_answers)
            is_fixed = (i in fixed_choices)

            if i == 0 and has_shuffle:
                marker = "(!x)" if is_correct else "(!)"
            elif is_fixed:
                marker = "(@x)" if is_correct else "(@)"
            else:
                marker = "(x)" if is_correct else "( )"

            markdown_content += f"{marker} {choice}\n"

    elif question_type == "multiple_select":
        choices = question_data.get('choices', [])
        correct_answers = question_data.get('correct_answers', [])

        for i, choice in enumerate(choices):
            marker = "[x]" if i in correct_answers else "[ ]"
            markdown_content += f"{marker} {choice}\n"

    elif question_type in ["text_input", "numerical"]:
        markdown_content += f"= {question_data.get('correct_answer', '')}\n"

    return markdown_content


def build_single_problem_xml(
    question_data: Dict[str, Any],
    display_name: Optional[str] = None,
    partial_credit: Optional[str] = None
) -> etree.Element:
    """
    Build a single <problem> XML etree.Element for a question matching
    OpenEdX Studio reference standard (library.mau_chuan.tar.gz).
    - Question prompt is wrapped in <p> inside response element (if question text is present)
    - No redundant <p/>, no <label> instruction tag
    - shuffle="true" ONLY when question has shuffle
    - fixed="true" ONLY when choice is in fixed_choices
    - multiple_select has no shuffle and no fixed attributes
    - partial_credit preserved on <choiceresponse>
    - markdown attribute has real \\n (lxml serializes to single &#10;)
    """
    tags_list = question_data.get('tags', [])
    if isinstance(tags_list, str):
        tags_list = [tags_list]

    tags_json = json.dumps([tag.replace('"', '\\"') for tag in tags_list], ensure_ascii=False)
    question_type = question_data.get("type", "multiple_choice")
    question_text = (question_data.get("question") or "").strip()

    if display_name is None:
        display_name = resolve_question_display_name(question_data, 0, {})

    problem_elem = etree.Element("problem", display_name=display_name, tags=tags_json)

    # Markdown content attribute with real \\n (DO NOT replace with &#10;)
    markdown_content = create_markdown_content(question_data)
    problem_elem.set("markdown", markdown_content)

    if question_type == "multiple_choice":
        mcr = etree.SubElement(problem_elem, "multiplechoiceresponse")
        if question_text:
            p = etree.SubElement(mcr, "p")
            p.text = question_text

        has_shuffle = bool(question_data.get('shuffle', False))
        cg_attrib = {"type": "MultipleChoice"}
        if has_shuffle:
            cg_attrib["shuffle"] = "true"
        cg = etree.SubElement(mcr, "choicegroup", attrib=cg_attrib)

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
        if question_text:
            p = etree.SubElement(cr, "p")
            p.text = question_text

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
        if question_text:
            p = etree.SubElement(sr, "p")
            p.text = question_text
        etree.SubElement(sr, "textline", attrib={"size": "20"})

    return problem_elem
