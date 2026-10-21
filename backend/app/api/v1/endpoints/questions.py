"""
Question processing endpoints
"""
from fastapi import APIRouter, Form, Query, Depends
from typing import Optional
import json
import re
from app.models.schemas.responses import QuestionProcessingResponse
from app.services.llm.base import LLMService
from app.api.dependencies import get_llm_service

router = APIRouter()


@router.post("/process", response_model=QuestionProcessingResponse)
async def process_questions(
    questions_text: str = Form(...),
    user_tags: str = Form("[]"),
    tags_explanation: str = Form(""),
    mode: str = Form(None),
    user_format: str = Form(None),
    provider: Optional[str] = Query(None),
    llm_service: LLMService = Depends(get_llm_service)
):
    """Process questions text and convert to structured format"""
    try:
        tags_list = json.loads(user_tags) if user_tags else []
        print(f"DEBUG: Received user_tags: {user_tags}")
        print(f"DEBUG: Parsed tags_list: {tags_list}")
        
        # Count number of questions (number of blocks)
        blocks = re.split(r'\n\s*\n', questions_text.strip())
        num_questions = len([b for b in blocks if b.strip()])
        
        # Choose mode if not provided
        if not mode:
            mode = 'llm' if num_questions <= 10 else 'custom'
        
        if mode == 'llm':
            # Call LLM to parse
            prompt = f"""
                BẠN LÀ CHUYÊN GIA PHÂN TÍCH CÂU HỎI TRẮC NGHIỆM. NHIỆM VỤ CỦA BẠN LÀ PHÂN TÍCH VĂN BẢN CÂU HỎI VÀ TRẢ VỀ ĐỊNH DẠNG JSON CHÍNH XÁC.

                ⚠️ QUAN TRỌNG: KHÔNG TẠO OUTLINE, CHỈ PHÂN TÍCH CÂU HỎI TRẮC NGHIỆM!

                QUY TẮC PHÂN TÍCH:
                1. Tìm các dòng bắt đầu bằng "de0", "de1", "de2", v.v. - đây là tags
                2. Tìm các câu hỏi (dòng không có marker (!), ( ), (x))
                3. Tìm các đáp án có marker (!), ( ), (x), (!x)
                4. Marker (x) = đáp án đúng
                5. Marker (!x) = đáp án đầu tiên VÀ đúng

                VÍ DỤ PHÂN TÍCH:
                Input:
                de0
                Generative AI tập trung vào việc phát triển các mô hình có khả năng nào?
                (!) Học từ dữ liệu đã có và tái tạo lại dữ liệu đó một cách chính xác.
                ( ) Phân tích dữ liệu hiện có và đưa ra dự đoán về tương lai.
                (x) Tự động tạo ra dữ liệu mới, sáng tạo nội dung mới dựa trên dữ liệu hiện có.
                ( ) Tối ưu hóa các thuật toán học máy để tăng hiệu suất.

                Output:
                {{
                "questions": [
                    {{
                    "question": "Generative AI tập trung vào việc phát triển các mô hình có khả năng nào?",
                    "choices": [
                        "Học từ dữ liệu đã có và tái tạo lại dữ liệu đó một cách chính xác.",
                        "Phân tích dữ liệu hiện có và đưa ra dự đoán về tương lai.",
                        "Tự động tạo ra dữ liệu mới, sáng tạo nội dung mới dựa trên dữ liệu hiện có.",
                        "Tối ưu hóa các thuật toán học máy để tăng hiệu suất."
                    ],
                    "correct_answers": [2],
                    "type": "multiple_choice",
                    "tags": ["de0", "Module 3-1 bai 1"]
                    }}
                ]
                }}

                YÊU CẦU:
                - PHẢI ĐẢM BẢO TRẢ VỀ ĐẦY ĐỦ SỐ LƯỢNG CÂU
                - PHÂN TÍCH TỪNG CÂU HỎI RIÊNG BIỆT
                - LẤY ĐẦY ĐỦ 4 ĐÁP ÁN CHO MỖI CÂU HỎI
                - XÁC ĐỊNH ĐÚNG ĐÁP ÁN ĐÚNG (index bắt đầu từ 0)
                - GÁN TAGS: de tag + tags từ người dùng (nếu có)
                - CHỈ TRẢ VỀ JSON VỚI KEY "questions", KHÔNG TẠO OUTLINE
                - KHÔNG GIẢI THÍCH, CHỈ TRẢ VỀ JSON

                DANH SÁCH CÂU HỎI CẦN PHÂN TÍCH:
                {questions_text}

                Tags người dùng: {', '.join(tags_list) if tags_list else 'không có'}
                Giải thích tags: {tags_explanation if tags_explanation else 'không có'}
                
                LƯU Ý: Nếu có tags từ người dùng, hãy thêm vào mảng tags của mỗi câu hỏi cùng với de tag.
                """
            
            result = llm_service.analyze_questions(questions_text, provider, prompt)
            
            # Debug: Log the LLM response
            print(f"DEBUG: LLM result type: {type(result)}")
            print(f"DEBUG: LLM result: {result}")
            
            # Handle different response formats
            if isinstance(result, str):
                # Check if this looks like a JSON response
                if result.strip().startswith('{') and '"questions"' in result:
                    try:
                        # Try to fix truncated JSON by finding the last complete question
                        result_str = result.strip()
                        
                        # Find the last complete question object
                        last_complete_brace = result_str.rfind('}')
                        if last_complete_brace > 0:
                            # Try to find the last complete question
                            questions_start = result_str.find('"questions":')
                            if questions_start > 0:
                                # Find the last complete question object
                                brace_count = 0
                                in_question = False
                                last_question_end = -1
                                
                                for i in range(questions_start, len(result_str)):
                                    if result_str[i:i+2] == '{"':
                                        brace_count += 1
                                        in_question = True
                                    elif result_str[i] == '}':
                                        brace_count -= 1
                                        if brace_count == 0 and in_question:
                                            last_question_end = i
                                            break
                                
                                if last_question_end > 0:
                                    # Truncate to last complete question
                                    fixed_json = result_str[:last_question_end + 1] + ']}'
                                    print(f"DEBUG: Fixed truncated JSON")
                                    parsed_result = json.loads(fixed_json)
                                    questions = parsed_result.get('questions', [])
                                    print(f"DEBUG: Parsed questions from fixed string: {len(questions)}")
                                else:
                                    # Fallback to original parsing
                                    parsed_result = json.loads(result_str)
                                    questions = parsed_result.get('questions', [])
                                    print(f"DEBUG: Parsed questions from string: {len(questions)}")
                            else:
                                parsed_result = json.loads(result_str)
                                questions = parsed_result.get('questions', [])
                                print(f"DEBUG: Parsed questions from string: {len(questions)}")
                        else:
                            parsed_result = json.loads(result_str)
                            questions = parsed_result.get('questions', [])
                            print(f"DEBUG: Parsed questions from string: {len(questions)}")
                            
                    except Exception as e:
                        print(f"DEBUG: Failed to parse JSON from string: {e}")
                        print(f"DEBUG: Raw result: {result[:500]}...")
                        questions = []
                else:
                    # This is not a JSON response, treat as raw text
                    print(f"DEBUG: Result is not JSON format, treating as raw text")
                    questions = []
            elif isinstance(result, dict):
                # Check if it's the expected question format
                if 'questions' in result:
                    questions = result.get('questions', [])
                    print(f"DEBUG: Found questions in dict: {len(questions)}")
                # If it's the outline format, extract questions if available
                elif 'outline' in result:
                    # Extract questions from outline format
                    questions = []
                    outline = result.get('outline', [])
                    print(f"DEBUG: Processing outline with {len(outline)} sections")
                    
                    # Map subsection titles to de tags based on position
                    de_tags = ['de0', 'de1', 'de2', 'de3', 'de4', 'de5','de6']
                    de_index = 0
                    
                    for section in outline:
                        print(f"DEBUG: Processing section: {section.get('title', 'N/A')}")
                        
                        # Handle different outline structures
                        if 'subsections' in section:
                            # Standard structure: section -> subsections -> units
                            for subsection in section.get('subsections', []):
                                # Check if subsection title is already a de tag
                                subsection_title = subsection.get('title', '')
                                if subsection_title.startswith('de') and subsection_title in de_tags:
                                    de_tag = subsection_title
                                    print(f"DEBUG: Found de tag in subsection title: {de_tag}")
                                else:
                                    # Use de tags based on position, not subsection title
                                    de_tag = de_tags[de_index] if de_index < len(de_tags) else f'de{de_index}'
                                    print(f"DEBUG: Processing subsection: {subsection_title} -> assigned tag: {de_tag}")
                                
                                for unit in subsection.get('units', []):
                                    question_text = unit.get('title', '')
                                    if question_text:
                                        questions.append({
                                            "question": question_text,
                                            "type": "multiple_choice",
                                            "choices": [],  # Will be filled by custom parser
                                            "correct_answers": [],
                                            "tags": [de_tag],
                                            "topic": "",
                                            "is_valid": True,
                                            "errors": []
                                        })
                                        print(f"DEBUG: Added question: {question_text[:50]}... with tags: {[de_tag]}")
                                de_index += 1
                        elif 'units' in section:
                            # Direct structure: section -> units
                            section_title = section.get('title', '')
                            if section_title.startswith('de') and section_title in de_tags:
                                de_tag = section_title
                                print(f"DEBUG: Found de tag in section title: {de_tag}")
                            else:
                                de_tag = de_tags[de_index] if de_index < len(de_tags) else f'de{de_index}'
                                print(f"DEBUG: Processing section: {section_title} -> assigned tag: {de_tag}")
                            
                            for unit in section.get('units', []):
                                question_text = unit.get('title', '')
                                if question_text:
                                    questions.append({
                                        "question": question_text,
                                        "type": "multiple_choice",
                                        "choices": [],  # Will be filled by custom parser
                                        "correct_answers": [],
                                        "tags": [de_tag],
                                        "topic": "",
                                        "is_valid": True,
                                        "errors": []
                                    })
                                    print(f"DEBUG: Added question: {question_text[:50]}... with tags: {[de_tag]}")
                            de_index += 1
                        else:
                            # Handle other structures - try to extract questions from any field
                            print(f"DEBUG: Unknown section structure, trying to extract questions")
                            for key, value in section.items():
                                if isinstance(value, list):
                                    for item in value:
                                        if isinstance(item, dict) and 'title' in item:
                                            question_text = item.get('title', '')
                                            if question_text:
                                                de_tag = de_tags[de_index] if de_index < len(de_tags) else f'de{de_index}'
                                                questions.append({
                                                    "question": question_text,
                                                    "type": "multiple_choice",
                                                    "choices": [],
                                                    "correct_answers": [],
                                                    "tags": [de_tag],
                                                    "topic": "",
                                                    "is_valid": True,
                                                    "errors": []
                                                })
                                                print(f"DEBUG: Added question from unknown structure: {question_text[:50]}... with tags: {[de_tag]}")
                                                de_index += 1
                                                break
                    print(f"DEBUG: Extracted {len(questions)} questions from outline")
                else:
                    # Try to parse as direct questions array
                    questions = result if isinstance(result, list) else []
                    print(f"DEBUG: Tried direct questions array: {len(questions)}")
            else:
                questions = []
                print(f"DEBUG: No questions found, result type: {type(result)}")
            
            # If LLM didn't return any questions or returned wrong format, fallback to custom parser
            if not questions:
                print(f"DEBUG: No questions extracted from LLM response, falling back to custom parser")
                print(f"DEBUG: LLM result type: {type(result)}")
                print(f"DEBUG: LLM result: {result}")
                print(f"DEBUG: Using tags_list for fallback: {tags_list}")
                questions = parse_questions_from_text(questions_text, tags_list, parse_group_tags=(mode == 'custom'))
                mode = 'custom'
                message = "Questions processed successfully using custom parser (LLM fallback)"
            else:
                print(f"DEBUG: Successfully extracted {len(questions)} questions from LLM response")
                
                # Check if all questions have complete data (choices, correct_answers, tags)
                complete_questions = []
                incomplete_questions = []
                
                for q in questions:
                    has_choices = q.get('choices') and len(q.get('choices', [])) > 0
                    has_answers = q.get('correct_answers') and len(q.get('correct_answers', [])) > 0
                    has_tags = q.get('tags') and len(q.get('tags', [])) > 0
                    
                    if has_choices and has_answers and has_tags:
                        complete_questions.append(q)
                    else:
                        incomplete_questions.append(q)
                
                print(f"DEBUG: Found {len(complete_questions)} complete questions and {len(incomplete_questions)} incomplete questions")
                
                if len(complete_questions) == len(questions):
                    # All questions are complete, use LLM response directly
                    print(f"DEBUG: All questions are complete, using LLM response directly")
                    questions = complete_questions
                else:
                    # Some questions are incomplete, use custom parser to fill missing data
                    print(f"DEBUG: Some questions incomplete, using custom parser to fill missing data")
                    questions_with_choices = parse_questions_from_text(questions_text, tags_list)
                    print(f"DEBUG: Custom parser returned {len(questions_with_choices)} questions")
                    
                    if questions_with_choices:
                        # Merge LLM tags with custom parser data for incomplete questions
                        for i, llm_q in enumerate(questions):
                            if i < len(questions_with_choices):
                                custom_q = questions_with_choices[i]
                                # Only fill missing data, keep LLM data if available
                                if not llm_q.get('choices') or len(llm_q.get('choices', [])) == 0:
                                    llm_q['choices'] = custom_q.get('choices', [])
                                if not llm_q.get('correct_answers') or len(llm_q.get('correct_answers', [])) == 0:
                                    llm_q['correct_answers'] = custom_q.get('correct_answers', [])
                                # Keep LLM tags (they are correct), only add user tags if needed
                                llm_tags = llm_q.get('tags', []).copy()
                                if tags_list and not tags_explanation:
                                    # Only add non-de user tags to avoid duplication
                                    non_de_user_tags = [tag for tag in tags_list if not tag.startswith('de')]
                                    for tag in non_de_user_tags:
                                        if tag not in llm_tags:
                                            llm_tags.append(tag)
                                llm_q['tags'] = llm_tags
                                print(f"DEBUG: Merged question {i+1}: tags={llm_q['tags']}, choices={len(llm_q['choices'])}, correct_answers={llm_q['correct_answers']}")
                
                # Add user tags if needed (for questions that don't have tags_explanation)
                if tags_list and not tags_explanation:
                    for i, llm_q in enumerate(questions):
                        llm_tags = llm_q.get('tags', []).copy()
                        # Only add non-de user tags to avoid duplication
                        non_de_user_tags = [tag for tag in tags_list if not tag.startswith('de')]
                        for tag in non_de_user_tags:
                            if tag not in llm_tags:
                                llm_tags.append(tag)
                        llm_q['tags'] = llm_tags

                message = "Questions processed successfully using LLM"

            # Apply user tags based on tags_explanation
            if tags_list and tags_explanation:
                questions = apply_user_tags_to_questions(questions, tags_list, tags_explanation)

            # Assign tags if missing and map answer -> correct_answers for frontend
            for q in questions:
                # Only assign non-de user tags if no tags exist
                if not q.get('tags') or not isinstance(q['tags'], list) or len(q['tags']) == 0:
                    non_de_user_tags = [tag for tag in tags_list if not tag.startswith('de')]
                    q['tags'] = non_de_user_tags
                # For questions with existing tags (from LLM), only add non-de user tags if no tags_explanation
                elif tags_list and not tags_explanation:
                    existing_tags = set(q['tags'])
                    # Only add non-de user tags to avoid duplication
                    non_de_user_tags = [tag for tag in tags_list if not tag.startswith('de')]
                    for tag in non_de_user_tags:
                        if tag not in existing_tags:
                            q['tags'].append(tag)
                if not q.get('correct_answers') and q.get('answer') is not None:
                    q['correct_answers'] = q['answer']

            return QuestionProcessingResponse(
                success=True,
                questions=questions,
                mode=mode,
                message=message
            )

        else:
            # Custom parser according to user format (if provided)
            if user_format == "multiple_select":
                questions = parse_multiple_select_questions_from_text(questions_text, tags_list, parse_group_tags=True)
            else:
                questions = parse_questions_from_text(questions_text, tags_list, parse_group_tags=True)
            
            # Apply user tags based on tags_explanation
            if tags_list and tags_explanation:
                questions = apply_user_tags_to_questions(questions, tags_list, tags_explanation)
            
            # Ensure all questions have tags
            for q in questions:
                q['tags'] = _merge_question_tags(q.get('tags', [])) if isinstance(q.get('tags'), list) else []
            
            return QuestionProcessingResponse(
                success=True,
                questions=questions,
                mode=mode,
                message="Questions processed successfully using custom parser"
            )
            
    except Exception as e:
        return QuestionProcessingResponse(
            success=False,
            questions=[],
            mode=mode or "unknown",
            message=f"Question processing failed: {str(e)}"
        )


@router.post("/from-library", response_model=QuestionProcessingResponse)
async def get_questions_from_library(
    tags: str = Form("[]"),
    count: int = Form(5)
):
    """Get questions from library based on tags"""
    try:
        # Parse tags
        tags_list = json.loads(tags) if tags else []
        
        # For now, return sample questions
        # In a real implementation, this would query the actual library
        sample_questions = [
            {
                "id": f"lib_q_{i}",
                "question": f"Câu hỏi mẫu {i+1} từ Library",
                "type": "multiple_choice",
                "choices": ["A", "B", "C", "D"],
                "correct_answers": [0],
                "tags": tags_list + ["mẫu"],
                "topic": "Chủ đề mẫu"
            }
            for i in range(min(count, 10))
        ]
        
        return QuestionProcessingResponse(
            success=True,
            questions=sample_questions,
            mode="library",
            message=f"Retrieved {len(sample_questions)} questions from library"
        )
        
    except Exception as e:
        return QuestionProcessingResponse(
            success=False,
            questions=[],
            mode="library",
            message=f"Failed to get questions from library: {str(e)}"
        )


def _parse_group_tag_marker(line):
    if not line.startswith('@tag:'):
        return None
    return [tag.strip() for tag in line[len('@tag:'):].split(',') if tag.strip()]


def _merge_question_tags(*tag_groups):
    tags = []
    for group in tag_groups:
        for tag in group:
            if tag and tag not in tags:
                tags.append(tag)
    return tags


def parse_questions_from_text(questions_text, tags_list=None, parse_group_tags=False):
    """Parser for new format: Question with (!), ( ), (x), (!x) markers"""
    print(f"DEBUG: parse_questions_from_text called with tags_list: {tags_list}")
    questions = []

    # Split into lines and process
    lines = [l.strip() for l in questions_text.strip().split('\n') if l.strip()]

    current_question = None
    current_choices = []
    current_correct_answer = None
    current_de_tag = None
    current_group_tags = []
    question_de_tag = None
    question_group_tags = []
    user_tags = [tag for tag in (tags_list or []) if not tag.startswith('de')]

    # Map de tags based on position
    de_tags = ['de0', 'de1', 'de2', 'de3', 'de4', 'de5', 'de6']
    de_index = 0

    for line in lines:
        group_tag_marker = _parse_group_tag_marker(line) if parse_group_tags else None
        if group_tag_marker is not None:
            current_group_tags = group_tag_marker
            continue

        # Check if line starts with de tag
        if line.startswith('de') and any(line.startswith(tag) for tag in de_tags):
            current_de_tag = line
            print(f"DEBUG: Found de tag: {current_de_tag}")
            continue
            
        # Check if line starts with marker pattern
        marker_match = re.match(r'^[\(\)!x\s]+', line)
        
        if not marker_match:
            # This is a question line (no markers)
            # If we have a previous question, save it
            if current_question and current_choices and current_correct_answer is not None:
                question_tags = _merge_question_tags(
                    [question_de_tag] if question_de_tag else [],
                    question_group_tags,
                    user_tags,
                )
                
                questions.append({
                    "question": current_question,
                    "type": "multiple_choice",
                    "choices": current_choices,
                    "correct_answers": [current_correct_answer],
                    "tags": question_tags,
                    "topic": "",
                    "is_valid": True,
                    "errors": []
                })
                print(f"DEBUG: Added question with tags: {question_tags}")
            
            # Start new question
            current_question = line.strip()
            question_de_tag = current_de_tag
            question_group_tags = current_group_tags
            current_choices = []
            current_correct_answer = None
        else:
            # This is a choice line with markers
            # Extract the choice text (remove the marker)
            choice_text = re.sub(r'^[\(\)!x\s]+', '', line).strip()
            if choice_text:  # Only add if there's actual text
                current_choices.append(choice_text)
                
                # Check if this is the correct answer
                # (!x) = đáp án đầu tiên VÀ đúng
                # (x) = đáp án đúng (không phải đầu tiên)
                if '(!x)' in line:
                    current_correct_answer = len(current_choices) - 1  # 0-based index
                elif '(x)' in line:
                    current_correct_answer = len(current_choices) - 1  # 0-based index
    
    # Don't forget the last question
    if current_question and current_choices and current_correct_answer is not None:
        question_tags = _merge_question_tags(
            [question_de_tag] if question_de_tag else [],
            question_group_tags,
            user_tags,
        )

        questions.append({
            "question": current_question,
            "type": "multiple_choice",
            "choices": current_choices,
            "correct_answers": [current_correct_answer],
            "tags": question_tags,
            "topic": "",
            "is_valid": True,
            "errors": []
        })
        print(f"DEBUG: Added last question with tags: {question_tags}")
    
    return questions


def parse_multiple_select_questions_from_text(questions_text, tags_list=None, parse_group_tags=False):
    """Parser for multiple selection format: [x]/[ ]"""
    questions = []
    lines = [l.strip() for l in questions_text.strip().split('\n') if l.strip()]
    current_question = None
    current_choices = []
    current_correct_answers = []
    current_de_tag = None
    current_group_tags = []
    question_de_tag = None
    question_group_tags = []
    user_tags = [tag for tag in (tags_list or []) if not tag.startswith('de')]
    de_tags = ['de0', 'de1', 'de2', 'de3', 'de4', 'de5', 'de6']
    de_index = 0
    for line in lines:
        group_tag_marker = _parse_group_tag_marker(line) if parse_group_tags else None
        if group_tag_marker is not None:
            current_group_tags = group_tag_marker
            continue

        # Check if line starts with de tag
        if line.startswith('de') and any(line.startswith(tag) for tag in de_tags):
            current_de_tag = line
            continue
        # Check if line is a question (not [x]/[ ])
        if not (line.startswith('[x]') or line.startswith('[ ]')):
            # Nếu có câu hỏi trước đó thì lưu lại
            if current_question and current_choices:
                question_tags = _merge_question_tags(
                    [question_de_tag] if question_de_tag else [],
                    question_group_tags,
                    user_tags,
                )
                questions.append({
                    "question": current_question,
                    "type": "multiple_select",
                    "choices": current_choices,
                    "correct_answers": current_correct_answers,
                    "tags": question_tags,
                    "topic": "",
                    "is_valid": True,
                    "errors": []
                })
            # Bắt đầu câu hỏi mới
            current_question = line.strip()
            question_de_tag = current_de_tag
            question_group_tags = current_group_tags
            current_choices = []
            current_correct_answers = []
        else:
            # Đây là đáp án
            is_correct = line.startswith('[x]')
            choice_text = line[3:].strip()
            if choice_text:
                current_choices.append(choice_text)
                if is_correct:
                    current_correct_answers.append(len(current_choices) - 1)
    # Đừng quên câu hỏi cuối cùng
    if current_question and current_choices:
        question_tags = _merge_question_tags(
            [question_de_tag] if question_de_tag else [],
            question_group_tags,
            user_tags,
        )
        questions.append({
            "question": current_question,
            "type": "multiple_select",
            "choices": current_choices,
            "correct_answers": current_correct_answers,
            "tags": question_tags,
            "topic": "",
            "is_valid": True,
            "errors": []
        })
    return questions


def apply_user_tags_to_questions(questions, tags_list, tags_explanation):
    """Apply user tags to questions based on tags_explanation"""
    if not tags_list or not tags_explanation:
        return questions
    
    # Parse tags_explanation to understand which tags apply to which questions
    explanation_lower = tags_explanation.lower()
    
    # Extract mentioned de tags from explanation
    mentioned_de_tags = []
    for tag in tags_list:
        if tag.startswith('de') and tag.lower() in explanation_lower:
            mentioned_de_tags.append(tag)
    
    print(f"DEBUG: tags_explanation: {tags_explanation}")
    print(f"DEBUG: mentioned_de_tags: {mentioned_de_tags}")
    
    for i, question in enumerate(questions):
        question_tags = question.get('tags', [])
        
        # Check if this question has a de tag that matches the explanation
        should_apply_user_tags = False
        
        # Look for de tags in the question's existing tags
        de_tags_in_question = [tag for tag in question_tags if tag.startswith('de')]
        
        if de_tags_in_question and mentioned_de_tags:
            # Check if any of the question's de tags are mentioned in the explanation
            for de_tag in de_tags_in_question:
                if de_tag in mentioned_de_tags:
                    should_apply_user_tags = True
                    print(f"DEBUG: Question {i+1} with de tag {de_tag} matches explanation")
                    break
        elif not mentioned_de_tags:
            # If no specific de tags mentioned in explanation, apply to all questions
            should_apply_user_tags = True
            print(f"DEBUG: No specific de tags mentioned, applying to all questions")
        
        if should_apply_user_tags:
            existing_tags = set(question_tags)
            # Only add non-de user tags (like "Module 3-1 bai 1")
            non_de_user_tags = [tag for tag in tags_list if not tag.startswith('de')]
            for tag in non_de_user_tags:
                if tag not in existing_tags:
                    question_tags.append(tag)
            question['tags'] = question_tags
            print(f"DEBUG: Applied user tags to question {i+1}: {question_tags}")
    
    return questions 