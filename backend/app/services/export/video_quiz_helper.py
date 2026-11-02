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
from lxml import etree
from app.services.export.helpers import (
    resolve_question_display_name,
    build_single_problem_xml,
    parse_group_tag_marker,
    match_radio_choice,
    match_checkbox_choice,
    merge_question_tags,
)


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
        prob_elem = build_single_problem_xml(q, display_name=display_name)
        prob_xml = etree.tostring(prob_elem, encoding="unicode", pretty_print=True)
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


def parse_video_quiz_text(
    content: Any,
    filename: str = "quiz.txt"
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Parse a text file containing in-video quiz questions.

    Supports:
    - UTF-8 with BOM or plain UTF-8 (utf-8-sig)
    - QuestionBank syntax:
      - Radio: (!), (x), ( ), (@), (@x)
      - Checkbox: [x], [ ], [X], []
      - @tag: persistent across questions until changed
      - @time: applies ONLY to the immediately following question
    - Automatic question type detection (multiple_choice vs multiple_select)
    - 1-based exact line numbering (preserving empty lines)
    - Full error collection across the entire file
    """
    if isinstance(content, bytes):
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            return [], [f"File '{filename}': File phải lưu dạng UTF-8."]
    elif isinstance(content, str):
        text = content
    else:
        return [], [f"File '{filename}': Định dạng nội dung không hợp lệ."]

    lines = text.splitlines()
    questions: List[Dict[str, Any]] = []
    errors: List[str] = []

    pending_time: Optional[Tuple[str, int]] = None  # (raw_str, line_idx)
    current_tags: List[str] = []

    current_prompt_lines: List[str] = []
    current_q_start_line: Optional[int] = None
    current_choices: List[Dict[str, Any]] = []
    current_choice_mode: Optional[str] = None  # 'radio' or 'checkbox'
    current_assigned_time: Optional[Tuple[str, int]] = None

    seen_seconds: Dict[int, Tuple[int, str]] = {}  # sec -> (line_idx, raw_ts)

    def finalize_question():
        nonlocal current_prompt_lines, current_q_start_line, current_choices, current_choice_mode, current_assigned_time
        if not current_prompt_lines and not current_choices:
            return

        q_line = current_q_start_line or 1
        prompt = "\n".join(current_prompt_lines).strip()
        prompt_preview = prompt.replace("\n", " ")[:30]

        if not prompt:
            errors.append(f"File '{filename}', Dòng {q_line}: Nội dung câu hỏi không được để trống.")

        # Check @time
        q_sec = None
        if not current_assigned_time:
            errors.append(
                f"File '{filename}', Dòng {q_line}: Câu hỏi '{prompt_preview}...' thiếu mốc thời gian @time: "
                f"(cần khai báo @time: MM:SS trước câu hỏi)."
            )
            raw_ts = None
        else:
            raw_ts, time_line = current_assigned_time
            try:
                sec = parse_timestamp_to_seconds(raw_ts)
                q_sec = sec
                if sec in seen_seconds:
                    prev_line, prev_ts = seen_seconds[sec]
                    errors.append(
                        f"File '{filename}', Dòng {time_line}: Mốc thời gian '{raw_ts}' ({sec}s) bị trùng với mốc '{prev_ts}' tại dòng {prev_line}. "
                        "Mỗi câu hỏi trong video phải có mốc thời gian xuất hiện riêng biệt, không được trùng lặp."
                    )
                else:
                    seen_seconds[sec] = (time_line, raw_ts)
            except ValueError as e:
                errors.append(f"File '{filename}', Dòng {time_line}: Mốc thời gian '{raw_ts}' không hợp lệ: {str(e)}")

        # Check choices count
        if len(current_choices) < 2:
            errors.append(f"File '{filename}', Dòng {q_line}: Câu hỏi phải có ít nhất 2 đáp án lựa chọn (hiện có {len(current_choices)}).")

        correct_indices = [i for i, c in enumerate(current_choices) if c["correct"]]
        fixed_indices = [i for i, c in enumerate(current_choices) if c["fixed"]]
        has_shuffle = any(c["shuffle"] for c in current_choices)

        if current_choice_mode == "radio":
            q_type = "multiple_choice"
            if len(correct_indices) == 0:
                errors.append(f"File '{filename}', Dòng {q_line}: Câu hỏi một đáp án phải có 1 đáp án đúng (x).")
            elif len(correct_indices) > 1:
                errors.append(f"File '{filename}', Dòng {q_line}: Câu hỏi một đáp án không được có nhiều hơn 1 đáp án đúng (tìm thấy {len(correct_indices)} đáp án đúng).")
        elif current_choice_mode == "checkbox":
            q_type = "multiple_select"
            if len(correct_indices) == 0:
                errors.append(f"File '{filename}', Dòng {q_line}: Câu hỏi nhiều đáp án phải có ít nhất 1 đáp án đúng [x].")
        else:
            q_type = "unknown"
            errors.append(f"File '{filename}', Dòng {q_line}: Câu hỏi không có lựa chọn đáp án hợp lệ (( ) hoặc [ ]).")

        questions.append({
            "question": prompt,
            "type": q_type,
            "timestamp": raw_ts,
            "seconds": q_sec,
            "line": q_line,
            "choices": [c["text"] for c in current_choices],
            "correct_answers": correct_indices,
            "fixed_choices": fixed_indices,
            "shuffle": has_shuffle,
            "tags": list(current_tags),
        })

        # Reset per-question state
        current_prompt_lines = []
        current_q_start_line = None
        current_choices = []
        current_choice_mode = None
        current_assigned_time = None

    for line_idx, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line:
            continue

        group_tags = parse_group_tag_marker(line)
        if group_tags is not None:
            current_tags = group_tags
            continue

        if line.startswith("@time:"):
            time_val = line[len("@time:"):].strip()
            # If we had a previous question with choices collected, finalize it first
            if current_choices:
                finalize_question()

            if pending_time is not None:
                errors.append(
                    f"File '{filename}', Dòng {line_idx}: Phát hiện hai chỉ thị @time: liên tiếp "
                    f"(dòng {pending_time[1]} và dòng {line_idx}) mà không có câu hỏi ở giữa."
                )
            pending_time = (time_val, line_idx)
            continue

        radio_m = match_radio_choice(line)
        box_m = match_checkbox_choice(line)

        if radio_m:
            if current_choice_mode == "checkbox":
                errors.append(
                    f"File '{filename}', Dòng {line_idx}: Không được trộn lẫn định dạng một đáp án ( ) "
                    f"vào câu hỏi nhiều đáp án [ ]."
                )
            else:
                current_choice_mode = "radio"

            inner = radio_m.group(1).strip()
            c_text = radio_m.group(2).strip()
            c_idx = len(current_choices)
            current_choices.append({
                "text": c_text,
                "correct": "x" in inner.lower(),
                "fixed": "@" in inner or ("!" in inner and c_idx > 0),
                "shuffle": "!" in inner and c_idx == 0,
                "line": line_idx
            })
        elif box_m:
            if current_choice_mode == "radio":
                errors.append(
                    f"File '{filename}', Dòng {line_idx}: Không được trộn lẫn định dạng nhiều đáp án [ ] "
                    f"vào câu hỏi một đáp án ( )."
                )
            else:
                current_choice_mode = "checkbox"

            inner = box_m.group(1).strip()
            c_text = box_m.group(2).strip()
            current_choices.append({
                "text": c_text,
                "correct": "x" in inner.lower(),
                "fixed": False,
                "shuffle": False,
                "line": line_idx
            })
        else:
            # Question prompt line
            if current_choices:
                finalize_question()

            if not current_prompt_lines:
                current_q_start_line = line_idx
                if pending_time is not None:
                    current_assigned_time = pending_time
                    pending_time = None

            current_prompt_lines.append(line)

    finalize_question()

    if pending_time is not None:
        errors.append(
            f"File '{filename}', Dòng {pending_time[1]}: Chỉ thị @time: '{pending_time[0]}' không có câu hỏi theo sau."
        )

    return questions, errors


def validate_and_prepare_video_quiz_units(
    outline: List[Dict[str, Any]],
    uploaded_txt_files: Dict[str, bytes]
) -> List[str]:
    """
    Validate all video_quiz units in outline and match against uploaded .txt files.
    Matches by EXACT FILENAME (case-insensitive), NO fuzzy/smart matching, NO fallback.
    Collects ALL errors in a single batch list.
    Populates unit['questions'] on successfully parsed units.
    """
    errors: List[str] = []
    uploaded_map = {fn.strip().lower(): (fn, data) for fn, data in uploaded_txt_files.items()}
    matched_keys = set()

    for chapter in outline:
        for subsection in chapter.get("subsections", []):
            for unit in subsection.get("units", []):
                u_type = (unit.get("type") or "").strip().lower()
                if u_type != "video_quiz":
                    continue

                u_title = unit.get("title", "Untitled Unit")
                v_url = unit.get("video_url") or ""

                # 1. Validate YouTube URL
                yt_id = extract_youtube_id(v_url)
                if not yt_id:
                    errors.append(
                        f"Unit '{u_title}': URL video '{v_url}' không phải là YouTube hợp lệ (ID 11 ký tự). "
                        "In-Video Quiz chỉ hỗ trợ video YouTube (không áp dụng với iframe/raw HTML/Google Drive theo mục 3.7 tài liệu hướng dẫn)."
                    )

                # 2. Check quiz file specification in unit
                raw_file = unit.get("quiz_file") or unit.get("content") or unit.get("file") or ""
                raw_file = str(raw_file).strip()
                if not raw_file:
                    errors.append(
                        f"Unit '{u_title}': Chưa khai báo tên file câu hỏi (.txt) trong cột Content."
                    )
                    continue

                norm_file = raw_file.lower()
                matched_key = None
                if norm_file in uploaded_map:
                    matched_key = norm_file
                elif f"{norm_file}.txt" in uploaded_map:
                    matched_key = f"{norm_file}.txt"

                if not matched_key:
                    errors.append(
                        f"Unit '{u_title}': Không tìm thấy file câu hỏi '{raw_file}' trong danh sách tải lên "
                        "(yêu cầu khớp tên chính xác, không dùng khớp gần đúng)."
                    )
                    continue

                real_fn, file_bytes = uploaded_map[matched_key]
                matched_keys.add(matched_key)

                # 3. Parse questions & collect errors
                unit_questions, parse_errors = parse_video_quiz_text(file_bytes, filename=real_fn)
                if parse_errors:
                    errors.extend(parse_errors)
                elif not unit_questions:
                    errors.append(f"File '{real_fn}': File không chứa câu hỏi nào hợp lệ.")
                else:
                    unit["questions"] = unit_questions

    # 4. Check for orphaned uploaded .txt files
    for norm_fn, (real_fn, _) in uploaded_map.items():
        if norm_fn not in matched_keys:
            errors.append(
                f"File '{real_fn}': File câu hỏi đã tải lên nhưng không khớp với bất kỳ unit 'video_quiz' nào trong outline."
            )

    return errors
