"""
Shared helper for in-video quiz component (invideoquiz_v2) and OpenEdX video/problem OLX generation.
"""
import os
import re
import uuid
import json
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urlparse, parse_qs
from app.services.export.helpers import resolve_question_display_name


def generate_uuid() -> str:
    """Generate 32-character hex UUID without hyphens."""
    return str(uuid.uuid4()).replace('-', '')


def extract_youtube_id(url: str) -> Optional[str]:
    """
    Extract 11-character YouTube video ID from various URL formats.
    
    Rejects:
    - HTML iframes / raw HTML (docs 3.7)
    - Google Drive / OneDrive / SharePoint URLs
    - Non-YouTube domains
    - Malformed or missing IDs
    
    Returns 11-char ID string if valid, otherwise None.
    """
    if not url or not isinstance(url, str):
        return None
    
    trimmed = url.strip()
    lower = trimmed.lower()
    
    # Reject raw HTML, iframes, embed wrappers, Google Drive
    if "<iframe" in lower or "<video" in lower or "<embed" in lower or "drive.google.com" in lower:
        return None
    
    try:
        parsed = urlparse(trimmed)
        host = (parsed.netloc or "").lower()
        
        # Must be youtube.com or youtu.be
        if "youtube.com" in host:
            # watch?v=ID
            qs = parse_qs(parsed.query)
            if "v" in qs and qs["v"]:
                vid = qs["v"][0]
                if re.fullmatch(r"[A-Za-z0-9_-]{11}", vid):
                    return vid
            # /embed/ID or /v/ID
            path_parts = [p for p in parsed.path.split("/") if p]
            if len(path_parts) >= 2 and path_parts[0] in ("embed", "v"):
                vid = path_parts[1]
                if re.fullmatch(r"[A-Za-z0-9_-]{11}", vid):
                    return vid
            # /shorts/ID
            if len(path_parts) >= 2 and path_parts[0] == "shorts":
                vid = path_parts[1]
                if re.fullmatch(r"[A-Za-z0-9_-]{11}", vid):
                    return vid
        
        if "youtu.be" in host:
            # youtu.be/ID
            path_parts = [p for p in parsed.path.split("/") if p]
            if path_parts:
                vid = path_parts[0]
                if re.fullmatch(r"[A-Za-z0-9_-]{11}", vid):
                    return vid
                    
        # Fallback standard pattern search
        m = re.search(r"(?:v=|\/embed\/|\/v\/|youtu\.be\/|\/shorts\/)([A-Za-z0-9_-]{11})", trimmed)
        if m:
            return m.group(1)
            
    except Exception:
        pass
        
    return None


def parse_timestamp_to_seconds(ts: Any) -> int:
    """
    Single canonical place to convert timestamps to integer seconds.
    
    Supports:
    - int or float: must be >= 0
    - str with pure digits: '60' -> 60
    - str with MM:SS: '01:30' -> 90
    - str with HH:MM:SS: '01:02:03' -> 3723
    
    Raises ValueError on invalid format, empty value, or negative value.
    """
    if ts is None:
        raise ValueError("Mốc thời gian không được để trống.")
    
    if isinstance(ts, (int, float)):
        sec = int(ts)
        if sec < 0:
            raise ValueError(f"Mốc thời gian không được âm: {sec}")
        return sec
        
    if isinstance(ts, str):
        s = ts.strip()
        if not s:
            raise ValueError("Mốc thời gian không được để trống.")
            
        # Pure seconds
        if s.isdigit():
            return int(s)
            
        parts = s.split(":")
        if len(parts) == 2:
            m_str, s_str = parts
            if m_str.isdigit() and s_str.isdigit() and len(s_str) == 2:
                sec = int(m_str) * 60 + int(s_str)
                if sec < 0:
                    raise ValueError(f"Mốc thời gian không được âm: {s}")
                return sec
        elif len(parts) == 3:
            h_str, m_str, s_str = parts
            if h_str.isdigit() and m_str.isdigit() and s_str.isdigit() and len(m_str) == 2 and len(s_str) == 2:
                sec = int(h_str) * 3600 + int(m_str) * 60 + int(s_str)
                if sec < 0:
                    raise ValueError(f"Mốc thời gian không được âm: {s}")
                return sec
                
    raise ValueError(f"Định dạng mốc thời gian không hợp lệ: '{ts}'. Cần dạng MM:SS hoặc số giây cố định.")


def build_single_problem_xml(question_data: Dict[str, Any], display_name: str) -> str:
    """
    Create a single problem XML file matching OpenEdX OLX format using real XML elements.
    Never assigns markup strings to .text, preventing XML escaping.
    """
    problem_elem = ET.Element("problem")
    problem_elem.set("display_name", display_name)

    # Optional tags attribute if provided
    tags_list = question_data.get("tags")
    if tags_list:
        if isinstance(tags_list, str):
            tags_list = [t.strip() for t in tags_list.split(",") if t.strip()]
        if isinstance(tags_list, list) and tags_list:
            problem_elem.set("tags", json.dumps(tags_list, ensure_ascii=False))

    q_type = question_data.get("type", "multiple_choice")
    q_text = question_data.get("question", "")
    choices = question_data.get("choices", [])
    correct_answers = question_data.get("correct_answers", [])
    if not correct_answers and "correct_answer" in question_data:
        ca = question_data["correct_answer"]
        if isinstance(ca, int):
            correct_answers = [ca]
        elif isinstance(ca, list):
            correct_answers = ca

    fixed_choices = question_data.get("fixed_choices", [])

    if q_type == "multiple_select":
        resp_elem = ET.SubElement(problem_elem, "choiceresponse")
        p_elem = ET.SubElement(resp_elem, "p")
        p_elem.text = q_text
        cbg_elem = ET.SubElement(resp_elem, "checkboxgroup")
        for i, choice in enumerate(choices):
            is_correct = "true" if i in correct_answers else "false"
            choice_attrs = {"correct": is_correct}
            if i in fixed_choices:
                choice_attrs["fixed"] = "true"
            c_elem = ET.SubElement(cbg_elem, "choice", attrib=choice_attrs)
            c_elem.text = str(choice)
    else:  # default multiple_choice
        resp_elem = ET.SubElement(problem_elem, "multiplechoiceresponse")
        p_elem = ET.SubElement(resp_elem, "p")
        p_elem.text = q_text
        cg_elem = ET.SubElement(resp_elem, "choicegroup")
        cg_elem.set("type", "MultipleChoice")
        cg_elem.set("shuffle", "true")
        for i, choice in enumerate(choices):
            is_correct = "true" if i in correct_answers else "false"
            choice_attrs = {"correct": is_correct}
            if i in fixed_choices:
                choice_attrs["fixed"] = "true"
            c_elem = ET.SubElement(cg_elem, "choice", attrib=choice_attrs)
            c_elem.text = str(choice)

    try:
        ET.indent(problem_elem, space="  ")
    except AttributeError:
        pass

    return ET.tostring(problem_elem, encoding="unicode")


def build_invideoquiz_unit(
    course_dir: str,
    unit_title: str,
    video_url: str,
    questions: List[Dict[str, Any]],
    vertical_id: Optional[str] = None,
    video_title: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a complete in-video quiz unit:
    1. Validates YouTube URL (must extract 11-char ID).
    2. Validates timestamps and rejects duplicates.
    3. Writes course/video/{video_id}.xml (matching OpenEdXExporter proven format).
    4. Writes course/problem/{problem_id}.xml for each question.
    5. Writes course/vertical/{vertical_id}.xml containing:
       - <video url_name="{video_id}"/>
       - <problem url_name="{problem_id}"/> ...
       - <invideoquiz_v2 url_name="{quiz_id}" xblock-family="xblock.v1" timemap="..." video_id="{video_id}"/>
    
    Returns metadata dict with generated IDs and timemap.
    """
    # 1. Validate YouTube URL
    yt_id = extract_youtube_id(video_url)
    if not yt_id:
        raise ValueError(
            "URL video không phải là YouTube hợp lệ (ID 11 ký tự). "
            "In-Video Quiz chỉ hỗ trợ video YouTube (không áp dụng với iframe/raw HTML theo mục 3.7 tài liệu hướng dẫn)."
        )
    
    # 2. Validate questions & timestamps
    if not questions or not isinstance(questions, list):
        raise ValueError("Danh sách câu hỏi không được rỗng.")
        
    parsed_questions: List[Tuple[int, Dict[str, Any]]] = []
    seen_seconds = set()
    
    for idx, q in enumerate(questions):
        raw_ts = q.get("timestamp")
        if raw_ts is None:
            raw_ts = q.get("seconds")
        
        sec = parse_timestamp_to_seconds(raw_ts)
        if sec in seen_seconds:
            ts_display = q.get("timestamp") or f"{sec}s"
            raise ValueError(
                f"Phát hiện mốc thời gian bị trùng lặp: {sec} giây ({ts_display}). "
                "Mỗi câu hỏi trong video phải có mốc thời gian xuất hiện riêng biệt, không được trùng lặp."
            )
        seen_seconds.add(sec)
        parsed_questions.append((sec, q))
        
    # Sort questions by timestamp ascending
    parsed_questions.sort(key=lambda x: x[0])
    
    # Ensure directories exist
    os.makedirs(os.path.join(course_dir, "video"), exist_ok=True)
    os.makedirs(os.path.join(course_dir, "problem"), exist_ok=True)
    os.makedirs(os.path.join(course_dir, "vertical"), exist_ok=True)
    
    # 3. Create Video XML
    video_id = generate_uuid()
    v_title = video_title or unit_title
    video_elem = ET.Element("video")
    video_elem.set("url_name", video_id)
    video_elem.set("display_name", v_title)
    video_elem.set("edx_video_id", generate_uuid())
    video_elem.set("youtube", f"1.00:{yt_id}")
    video_elem.set("youtube_id_1_0", yt_id)
    video_elem.set("html5_sources", "[]")
    video_elem.set("transcripts", "{}")
    ET.SubElement(video_elem, "video_asset", {
        "client_video_id": "External Video",
        "duration": "0.0",
        "image": ""
    })
    
    video_xml = ET.tostring(video_elem, encoding="unicode")
    with open(os.path.join(course_dir, "video", f"{video_id}.xml"), "w", encoding="utf-8") as f:
        f.write(video_xml)
        
    # 4. Create Problem XMLs and build Timemap
    used_names: Dict[str, int] = {}
    problem_ids: List[str] = []
    timemap: Dict[str, str] = {}
    
    for idx, (sec, q) in enumerate(parsed_questions):
        raw_pid = q.get("id")
        # Ensure 32-char hex url_name (without prefixes like 'q_')
        if raw_pid and re.fullmatch(r"[0-9a-fA-F]{32}", str(raw_pid)):
            prob_id = str(raw_pid).lower()
        else:
            prob_id = generate_uuid()
            
        problem_ids.append(prob_id)
        timemap[str(sec)] = prob_id
        
        display_name = resolve_question_display_name(q, idx, used_names)
        prob_xml = build_single_problem_xml(q, display_name)
        with open(os.path.join(course_dir, "problem", f"{prob_id}.xml"), "w", encoding="utf-8") as f:
            f.write(prob_xml)
            
    # 5. Create Vertical XML
    vert_id = vertical_id or generate_uuid()
    vert_elem = ET.Element("vertical")
    vert_elem.set("display_name", unit_title)
    
    # Add <video url_name="{video_id}"/>
    video_ref = ET.SubElement(vert_elem, "video")
    video_ref.set("url_name", video_id)
    
    # Add <problem url_name="{prob_id}"/>
    for pid in problem_ids:
        prob_ref = ET.SubElement(vert_elem, "problem")
        prob_ref.set("url_name", pid)
        
    # Add <invideoquiz_v2>
    quiz_id = generate_uuid()
    quiz_elem = ET.SubElement(vert_elem, "invideoquiz_v2")
    quiz_elem.set("url_name", quiz_id)
    quiz_elem.set("xblock-family", "xblock.v1")
    quiz_elem.set("timemap", json.dumps(timemap, ensure_ascii=False, indent=2))
    quiz_elem.set("video_id", video_id)
    
    vert_xml = ET.tostring(vert_elem, encoding="unicode")
    with open(os.path.join(course_dir, "vertical", f"{vert_id}.xml"), "w", encoding="utf-8") as f:
        f.write(vert_xml)
        
    return {
        "vertical_id": vert_id,
        "video_id": video_id,
        "quiz_id": quiz_id,
        "problem_ids": problem_ids,
        "timemap": timemap,
        "vertical_xml": vert_xml,
    }
