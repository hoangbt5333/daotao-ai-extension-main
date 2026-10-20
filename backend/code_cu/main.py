import os
import tempfile
import shutil
from typing import Optional, List
from fastapi import FastAPI, File, UploadFile, Form, Query, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import json

from extractors import extract_text_from_file
from llm import analyze_text_with_llm, get_available_providers, get_default_provider
from openedx_exporter import export_openedx_structure
from tar_packager import make_tarfile, cleanup_temp_directory
from library_exporter import export_library_to_tar
from exam_exporter import export_exam_to_tar
from video_quiz_exporter import export_video_quiz_to_tar
from config import config

# Create exports directory if it doesn't exist
EXPORTS_DIR = "exports"
os.makedirs(EXPORTS_DIR, exist_ok=True)

app = FastAPI(title="Daotao AI Extension API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for exports
app.mount("/exports", StaticFiles(directory=EXPORTS_DIR), name="exports")

@app.get("/")
async def root():
    return {
        "message": "Daotao AI Extension API",
        "version": "1.0.0",
        "endpoints": {
            "upload": "/upload/",
            "analyze": "/analyze/",
            "export": "/export/",
            "map-pdfs": "/map-pdfs/",
            "providers": "/providers/",
            "process-questions": "/process-questions/",
            "export-library": "/export-library/",
            "get-questions-from-library": "/get-questions-from-library/",
            "export-exam": "/export-exam/",
            "export-exam-subsection": "/export-exam-subsection/",
            "export-exam-questions-library": "/export-exam-questions-library/",
            "export-exam-section": "/export-exam-section/",
            "export-video-quiz": "/export-video-quiz/"
        }
    }

@app.get("/providers/")
async def get_providers():
    """Get available LLM providers"""
    return {
        "available": get_available_providers(),
        "default": get_default_provider()
    }

@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    """Upload and extract text from file"""
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        # Extract text
        text = extract_text_from_file(temp_file_path)
        
        # Clean up temp file
        os.unlink(temp_file_path)
        
        return {"text": text[:1000] + "..." if len(text) > 1000 else text}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/analyze/")
async def analyze_text(
    text: str = Form(...),
    provider: Optional[str] = Query(None)
):
    """Analyze text and generate outline + questions"""
    try:
        result = analyze_text_with_llm(text, provider)
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/map-pdfs/")
async def map_pdfs_to_outline(
    files: list[UploadFile] = File(...),
    outline: str = Form(...)
):
    """Map PDF files to outline based on filename analysis"""
    try:
        # Parse outline
        outline_data = json.loads(outline)
        
        # Analyze filenames and map to outline
        mapped_outline = await map_pdf_files_to_outline(files, outline_data)
        
        return {
            "success": True,
            "mapped_outline": mapped_outline,
            "mapped_count": len(files)
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

async def map_pdf_files_to_outline(files: list[UploadFile], outline_data: dict) -> dict:
    """Map PDF files to outline using filename analysis"""
    # Create a copy of outline to modify
    mapped_outline = json.loads(json.dumps(outline_data))
    
    print(f"Starting PDF mapping for {len(files)} files")
    print(f"Original outline structure: {len(mapped_outline.get('outline', []))} chapters")
    
    # Analyze each PDF filename
    for file in files:
        filename = file.filename
        if not filename.lower().endswith('.pdf'):
            continue
            
        print(f"\nProcessing file: {filename}")
        
        # Analyze filename pattern to determine mapping
        mapping = analyze_filename_pattern(filename, mapped_outline)
        
        print(f"Filename analysis result: {mapping}")
        
        if mapping and mapping.get('confidence', 0) > 0.3:
            # Apply mapping to outline
            apply_mapping_to_outline(mapped_outline, filename, mapping)
        else:
            print(f"Low confidence mapping for {filename}, using fallback")
            # Fallback: add to first available unit
            add_file_to_first_available_unit(mapped_outline, filename)
    
    # Print final outline structure
    print(f"\nFinal outline structure after mapping:")
    for i, chapter in enumerate(mapped_outline.get('outline', [])):
        print(f"Chapter {i}: {chapter.get('title', 'Untitled')}")
        for j, subsection in enumerate(chapter.get('subsections', [])):
            print(f"  Subsection {j}: {subsection.get('title', 'Untitled')} - {len(subsection.get('units', []))} units")
    
    return mapped_outline

def analyze_filename_pattern(filename: str, outline_data: dict) -> dict:
    """Analyze filename pattern to determine chapter and subsection mapping"""
    import re
    
    # Remove extension
    name = filename.replace('.pdf', '').replace('.PDF', '')
    
    print(f"Analyzing filename pattern: {name}")
    
    # Pattern: Bài X-Y.pdf (Chương X, bài Y)
    pattern = re.match(r'Bài\s*(\d+)[-–](\d+(?:\.\d+)?)', name)
    if pattern:
        chapter_num = int(pattern.group(1))
        bai_str = pattern.group(0).replace(' ', '')  # "Bài6-3"
        bai_num = pattern.group(2)  # "3" hoặc "3.1"
        chapter_index = chapter_num - 1
        if chapter_index < len(outline_data.get('outline', [])):
            chapter = outline_data['outline'][chapter_index]
            # Tìm subsection có tiêu đề chứa "Bài X-Y" hoặc "X-Y"
            for sub_idx, subsection in enumerate(chapter.get('subsections', [])):
                sub_title = subsection.get('title', '').replace(' ', '')
                if f"Bài{chapter_num}-{bai_num}" in sub_title or f"{chapter_num}-{bai_num}" in sub_title:
                    return {
                        "chapter_index": chapter_index,
                        "subsection_index": sub_idx,
                        "unit_title": generate_unit_title_from_filename(filename),
                        "confidence": 0.95
                    }
            # Nếu không tìm thấy, fallback về subsection đầu tiên
            return {
                "chapter_index": chapter_index,
                "subsection_index": 0,
                "unit_title": generate_unit_title_from_filename(filename),
                "confidence": 0.8
            }
    # Fallback: logic cũ
    # Pattern 1: C_X_Y.pdf (Chapter X, Subsection Y)
    pattern1 = re.match(r'C_(\d+)_(\d+)', name)
    if pattern1:
        chapter_num = int(pattern1.group(1))
        subsection_num = int(pattern1.group(2))
        print(f"Pattern 1 match: Chapter {chapter_num}, Subsection {subsection_num}")
        
        # Adjust chapter index (chapters start from 1, array starts from 0)
        chapter_index = chapter_num - 1
        subsection_index = subsection_num - 1
        
        if chapter_index < len(outline_data.get('outline', [])):
            chapter = outline_data['outline'][chapter_index]
            if subsection_index < len(chapter.get('subsections', [])):
                return {
                    "chapter_index": chapter_index,
                    "subsection_index": subsection_index,
                    "unit_title": generate_unit_title_from_filename(filename),
                    "confidence": 0.9
                }
    
    # Pattern 2: C_X.pdf (Chapter X, first subsection)
    pattern2 = re.match(r'C_(\d+)', name)
    if pattern2:
        chapter_num = int(pattern2.group(1))
        chapter_index = chapter_num - 1
        
        if chapter_index < len(outline_data.get('outline', [])):
            return {
                "chapter_index": chapter_index,
                "subsection_index": 0,  # First subsection
                "unit_title": generate_unit_title_from_filename(filename),
                "confidence": 0.8
            }
    
    # Pattern 3: Theory_X_Y.pdf (Theory chapter X, subsection Y)
    pattern3 = re.match(r'Theory_(\d+)_(\d+)', name)
    if pattern3:
        chapter_num = int(pattern3.group(1))
        subsection_num = int(pattern3.group(2))
        chapter_index = chapter_num - 1
        subsection_index = subsection_num - 1
        
        if chapter_index < len(outline_data.get('outline', [])):
            chapter = outline_data['outline'][chapter_index]
            if subsection_index < len(chapter.get('subsections', [])):
                return {
                    "chapter_index": chapter_index,
                    "subsection_index": subsection_index,
                    "unit_title": generate_unit_title_from_filename(filename),
                    "confidence": 0.9
                }
    
    # Pattern 4: Theory_X.pdf (Theory chapter X, first subsection)
    pattern4 = re.match(r'Theory_(\d+)', name)
    if pattern4:
        chapter_num = int(pattern4.group(1))
        chapter_index = chapter_num - 1
        
        if chapter_index < len(outline_data.get('outline', [])):
            return {
                "chapter_index": chapter_index,
                "subsection_index": 0,
                "unit_title": generate_unit_title_from_filename(filename),
                "confidence": 0.8
            }
    
    # Pattern 5: Look for chapter numbers in filename
    chapter_match = re.search(r'chương\s*(\d+)|chapter\s*(\d+)|c(\d+)', name.lower())
    if chapter_match:
        chapter_num = int(chapter_match.group(1) or chapter_match.group(2) or chapter_match.group(3))
        chapter_index = chapter_num - 1
        
        if chapter_index < len(outline_data.get('outline', [])):
            return {
                "chapter_index": chapter_index,
                "subsection_index": 0,
                "unit_title": generate_unit_title_from_filename(filename),
                "confidence": 0.7
            }
    
    # Pattern 6: Try to match by keywords in chapter titles
    keywords = name.replace('_', ' ').replace('-', ' ').split()
    best_match = find_best_chapter_match_by_keywords(keywords, outline_data.get('outline', []))
    
    if best_match is not None:
        return {
            "chapter_index": best_match,
            "subsection_index": 0,
            "unit_title": generate_unit_title_from_filename(filename),
            "confidence": 0.6
        }
    
    return None

def find_best_chapter_match_by_keywords(keywords: list, chapters: list) -> int:
    """Find best matching chapter based on keywords"""
    if not chapters or not keywords:
        return None
    
    best_match = 0
    best_score = 0
    
    for i, chapter in enumerate(chapters):
        chapter_title = chapter.get('title', '').lower()
        score = sum(1 for keyword in keywords if keyword.lower() in chapter_title)
        if score > best_score:
            best_score = score
            best_match = i
    
    return best_match if best_score > 0 else None

def generate_unit_title_from_filename(filename: str) -> str:
    """Generate unit title from filename"""
    # Remove extension and common prefixes
    title = filename.replace('.pdf', '').replace('.PDF', '')
    
    # Replace underscores and dashes with spaces
    title = title.replace('_', ' ').replace('-', ' ')
    
    # Capitalize first letter of each word
    title = ' '.join(word.capitalize() for word in title.split())
    
    return title

def parse_mapping_response(response: str) -> dict:
    """Parse LLM response as mapping information"""
    try:
        # Try to extract JSON from response
        import re
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except:
        pass
    return None

def apply_mapping_to_outline(outline: dict, filename: str, mapping: dict):
    """Apply mapping to outline structure"""
    try:
        chapter_index = mapping.get('chapter_index', 0)
        subsection_index = mapping.get('subsection_index', 0)
        unit_title = mapping.get('unit_title', generate_unit_title_from_filename(filename))
        
        print(f"Applying mapping: {filename} -> Chapter {chapter_index}, Subsection {subsection_index}, Title: {unit_title}")
        
        if (chapter_index < len(outline.get('outline', [])) and 
            subsection_index < len(outline['outline'][chapter_index].get('subsections', []))):
            
            # Add unit to the specified subsection
            unit = {
                "title": unit_title,
                "type": "pdf",
                "file": filename
            }
            
            # Ensure units array exists
            if 'units' not in outline['outline'][chapter_index]['subsections'][subsection_index]:
                outline['outline'][chapter_index]['subsections'][subsection_index]['units'] = []
            
            outline['outline'][chapter_index]['subsections'][subsection_index]['units'].append(unit)
            print(f"Successfully added unit: {unit_title}")
        else:
            print(f"Invalid indices: chapter_index={chapter_index}, subsection_index={subsection_index}")
            print(f"Available chapters: {len(outline.get('outline', []))}")
            if outline.get('outline') and chapter_index < len(outline['outline']):
                print(f"Available subsections in chapter {chapter_index}: {len(outline['outline'][chapter_index].get('subsections', []))}")
    except Exception as e:
        print(f"Error applying mapping: {e}")

def add_file_to_first_available_unit(outline: dict, filename: str):
    """Fallback: add file to first available unit"""
    try:
        if not outline.get('outline'):
            return
        
        # Find first chapter with subsections
        for chapter_idx, chapter in enumerate(outline['outline']):
            if chapter.get('subsections'):
                # Add to first subsection
                unit = {
                    "title": generate_unit_title_from_filename(filename),
                    "type": "pdf",
                    "file": filename
                }
                
                # Ensure units array exists
                if 'units' not in chapter['subsections'][0]:
                    chapter['subsections'][0]['units'] = []
                
                chapter['subsections'][0]['units'].append(unit)
                print(f"Fallback: Added {filename} to chapter {chapter_idx}, first subsection")
                break
    except Exception as e:
        print(f"Error adding file to first unit: {e}")

@app.post("/export/")
async def export_openedx(
    files: List[UploadFile] = File([]),
    outline: str = Form(...),
    questions: str = Form(...),
    filename: Optional[str] = Query(...)
):
    """Export outline and questions to Open edX format, nhận file PDF upload từ người dùng"""
    import json
    try:
        outline_data = json.loads(outline)
        questions_data = json.loads(questions)
        print("[EXPORT] Received outline:", outline_data)
        print("[EXPORT] Received questions:", questions_data)
        print("[EXPORT] Filename:", filename)
        print(f"[EXPORT] Received {len(files)} PDF files from user upload.")
        # Create safe filename
        safe_filename = "".join(c for c in filename if c.isalnum() or c in ('-', '_', '.'))
        if not safe_filename:
            safe_filename = "course_export"
        
        # Create temporary directory for export
        temp_dir = tempfile.mkdtemp()
        tar_name = f"{safe_filename}.tar.gz"
        tar_path = os.path.join(EXPORTS_DIR, tar_name)
        
        try:
            # Đảm bảo outline là list chương
            outline_list = outline_data['outline'] if isinstance(outline_data, dict) and 'outline' in outline_data else outline_data
            export_openedx_structure(outline_list, questions_data, temp_dir, uploaded_pdfs=files)
            
            # Create tar.gz file
            tar_success = make_tarfile(tar_path, temp_dir)
            if not tar_success or not os.path.exists(tar_path):
                raise Exception(f"Không tạo được file tar: {tar_path}")
            
            # Return file path for download
            tar_file = f"/exports/{tar_name}"
            
            return {"tar_file": tar_file}
            
        finally:
            # Clean up temporary directory
            cleanup_temp_directory(temp_dir)
            
    except Exception as e:
        import traceback
        print("[EXPORT] Exception:", str(e))
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})

def parse_questions_from_text(questions_text, tags_list=None):
    # Parser cho format mới: Câu hỏi, A/B/C/D, Đáp án
    import re
    questions = []
    
    # Tách từng block câu hỏi (cách nhau bởi dòng trống)
    blocks = re.split(r'\n\s*\n', questions_text.strip())
    
    for block in blocks:
        lines = [l.strip() for l in block.strip().split('\n') if l.strip()]
        if not lines:
            continue
            
        # Tìm dòng bắt đầu bằng "Câu hỏi:"
        question_line = None
        choices = []
        correct_answer = None
        
        for line in lines:
            if line.startswith('Câu hỏi:'):
                question_line = line.replace('Câu hỏi:', '').strip()
            elif line.startswith('Đáp án:'):
                # Xử lý đáp án đúng
                answer_part = line.replace('Đáp án:', '').strip()
                # Tìm chữ cái A, B, C, D trong đáp án
                answer_match = re.search(r'[A-D]', answer_part.upper())
                if answer_match:
                    correct_answer = ord(answer_match.group()) - 65  # A=0, B=1, C=2, D=3
            elif re.match(r'^[A-D]\.', line):
                # Xử lý các lựa chọn A, B, C, D
                choice_text = re.sub(r'^[A-D]\.\s*', '', line).strip()
                choices.append(choice_text)
        
        # Chỉ tạo câu hỏi nếu có đủ thông tin
        if question_line and choices and correct_answer is not None:
            questions.append({
                "question": question_line,
                "type": "multiple_choice",
                "choices": choices,
                "correct_answers": [correct_answer],
                "tags": tags_list if tags_list else [],
                "topic": "",
                "is_valid": True,
                "errors": []
            })
    
    return questions

@app.post("/process-questions/")
async def process_questions(
    questions_text: str = Form(...),
    user_tags: str = Form("[]"),
    tags_explanation: str = Form(""),
    mode: str = Form(None),
    user_format: str = Form(None),
    provider: Optional[str] = Query(None)
):
    try:
        tags_list = json.loads(user_tags) if user_tags else []
        # Đếm số câu hỏi (số block)
        import re
        blocks = re.split(r'\n\s*\n', questions_text.strip())
        num_questions = len([b for b in blocks if b.strip()])
        # Chọn mode nếu chưa truyền
        if not mode:
            mode = 'llm' if num_questions <= 10 else 'custom'
        if mode == 'llm':
            # Gọi LLM để parse
            prompt = f"""
                Hãy phân tích và chuyển đổi danh sách câu hỏi sau về định dạng chuẩn Open edX JSON.

                YÊU CẦU:
                - Trả về đầy đủ danh sách câu hỏi, không được thiếu câu nào
                - Mỗi câu hỏi BẮT BUỘC phải có trường "tags" là mảng string (ví dụ: ["đấu thầu", "CD2"]). Nếu không có tags thì để là mảng rỗng [].
                - Nếu là trắc nghiệm, hãy nhận diện loại (1 đáp án đúng: multiple_choice, nhiều đáp án đúng: multiple_select).
                - Nếu là tự luận (text input) hoặc điền số (numerical), hãy nhận diện đúng type.
                - Với mỗi câu hỏi trắc nghiệm, hãy xác định rõ đáp án đúng và trả về trường "correct_answers" là mảng chỉ số (bắt đầu từ 0, ví dụ: [1] nếu đáp án đúng là B).
                - Nếu nhiều đáp án đúng, trả về mảng nhiều số (ví dụ: [0,2] nếu đúng là A và C).
                - Nếu là tự luận hoặc numerical, trường "correct_answers" là mảng rỗng [].
                - Nếu có tags người dùng cung cấp, hãy ưu tiên gán các tags này nếu phù hợp, đồng thời bổ sung tags tự động nếu cần.

                DANH SÁCH CÂU HỎI:
                {questions_text}

                Tags người dùng: {', '.join(tags_list)}
                Giải thích tags: {tags_explanation}

                TRẢ VỀ JSON format như sau (KHÔNG giải thích gì thêm, chỉ trả về JSON):
                {{
                "questions": [
                    {{
                    "question": "Nội dung câu hỏi",
                    "choices": ["Đáp án A", "Đáp án B", "Đáp án C", "Đáp án D"],
                    "correct_answers": [1],
                    "type": "multiple_choice",
                    "tags": [{','.join(tags_list)}]
                    }},
                    ...
                ]
                }}
                """
            result = analyze_text_with_llm(prompt, provider)
            print(f"prompt:{prompt}")
            print(f"LLM result: {result}")
            if isinstance(result, str):
                try:
                    parsed_result = json.loads(result)
                    questions = parsed_result.get('questions', [])
                except Exception as e:
                    print(f"LLM trả về không phải JSON: {e}")
                    questions = []
            elif isinstance(result, dict):
                questions = result.get('questions', [])
            else:
                questions = []
            # Gán tags nếu thiếu và map answer -> correct_answers cho frontend
            for q in questions:
                if not q.get('tags') or not isinstance(q['tags'], list) or len(q['tags']) == 0:
                    q['tags'] = tags_list
                if not q.get('correct_answers') and q.get('answer') is not None:
                    q['correct_answers'] = q['answer']
            return {"success": True, "data": {"questions": questions}}
        else:
            # Custom parser theo format user cung cấp (nếu có)
            # Hiện tại chỉ dùng parse_questions_from_text, có thể mở rộng sau
            questions = parse_questions_from_text(questions_text, tags_list)
            for q in questions:
                if not q.get('tags') or not isinstance(q['tags'], list) or len(q['tags']) == 0:
                    q['tags'] = tags_list
            return {"success": True, "data": {"questions": questions}}
    except Exception as e:
        print(f"Error processing questions: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/export-library/")
async def export_library(
    questions: str = Form(...),
    library_name: str = Form(...),
    org: str = Form("SoDiTEC"),
    library_code: str = Form("2025-2"),
    start_time: str = Form(None),
    filename: Optional[str] = Query(None)
):
    """Export questions as Library format"""
    try:
        # Parse questions
        questions_data = json.loads(questions)
        questions_list = questions_data.get("questions", [])
        
        # Create safe filename
        safe_filename = "".join(c for c in (filename or library_name) if c.isalnum() or c in ('-', '_', '.'))
        if not safe_filename:
            safe_filename = "library_export"
        
        # Create tar.gz file
        tar_name = f"{safe_filename}.tar.gz"
        tar_path = os.path.join(EXPORTS_DIR, tar_name)
        
        # Xử lý start_time: luôn có dấu nháy kép thật
        if start_time:
            if not (start_time.startswith('"') and start_time.endswith('"')):
                start_time = f'"{start_time.strip()}"'
        else:
            start_time = '"2030-01-01T00:00:00Z"'
        # Export library (truyền org, library_code, start_time)
        success = export_library_to_tar(questions_list, library_name, tar_path, org=org, library_code=library_code, start_time=start_time)
        
        if success and os.path.exists(tar_path):
            return {"tar_file": f"/exports/{tar_name}"}
        else:
            raise Exception("Không tạo được file Library")
            
    except Exception as e:
        print(f"Error exporting library: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/get-questions-from-library/")
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
        
        return {
            "success": True,
            "questions": sample_questions
        }
    except Exception as e:
        print(f"Error getting questions from library: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/export-exam/")
async def export_exam(
    exam_name: str = Form(...),
    exam_description: str = Form(""),
    total_time: int = Form(90),
    is_timed: bool = Form(True),
    sections: str = Form(...),
    filename: Optional[str] = Query(None)
):
    """Export exam as Open edX format"""
    try:
        # Parse sections
        sections_data = json.loads(sections)
        
        # Create exam data
        exam_data = {
            "exam_name": exam_name,
            "exam_description": exam_description,
            "total_time": total_time,
            "is_timed": is_timed,
            "sections": sections_data
        }
        
        # Create safe filename
        safe_filename = "".join(c for c in (filename or exam_name) if c.isalnum() or c in ('-', '_', '.'))
        if not safe_filename:
            safe_filename = "exam_export"
        
        # Create tar.gz file
        tar_name = f"{safe_filename}.tar.gz"
        tar_path = os.path.join(EXPORTS_DIR, tar_name)
        
        # Export exam
        success = export_exam_to_tar(exam_data, tar_path)
        
        if success and os.path.exists(tar_path):
            return {"tar_file": f"/exports/{tar_name}"}
        else:
            raise Exception("Không tạo được file Exam")
            
    except Exception as e:
        print(f"Error exporting exam: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/export-exam-subsection/")
async def export_exam_subsection(
    exam_name: str = Form(...),
    exam_description: str = Form(""),
    total_time: int = Form(90),
    is_timed: bool = Form(True),
    sections: str = Form(...),
    filename: Optional[str] = Query(None)
):
    """Export đề thi dạng subsection để thêm vào course có sẵn"""
    try:
        # Parse sections
        sections_data = json.loads(sections)
        
        # Create exam data
        exam_data = {
            "exam_name": exam_name,
            "exam_description": exam_description,
            "total_time": total_time,
            "is_timed": is_timed,
            "sections": sections_data
        }
        
        # Create safe filename
        safe_filename = "".join(c for c in (filename or exam_name) if c.isalnum() or c in ('-', '_', '.'))
        if not safe_filename:
            safe_filename = "exam_subsection_export"
        
        # Create tar.gz file
        tar_name = f"{safe_filename}.tar.gz"
        tar_path = os.path.join(EXPORTS_DIR, tar_name)
        
        # Export exam subsection
        from exam_exporter import export_exam_as_subsection_only
        success = export_exam_as_subsection_only(exam_data, tar_path)
        
        if success and os.path.exists(tar_path):
            return {"tar_file": f"/exports/{tar_name}"}
        else:
            raise Exception("Không tạo được file Exam Subsection")
            
    except Exception as e:
        print(f"Error exporting exam subsection: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/export-exam-questions-library/")
async def export_exam_questions_library(
    sections: str = Form(...),
    filename: Optional[str] = Query(None)
):
    """Export câu hỏi từ đề thi dạng Library"""
    try:
        # Parse sections
        sections_data = json.loads(sections)
        
        # Create safe filename
        safe_filename = "".join(c for c in (filename or "exam_questions_library") if c.isalnum() or c in ('-', '_', '.'))
        if not safe_filename:
            safe_filename = "exam_questions_library"
        
        # Create tar.gz file
        tar_name = f"{safe_filename}.tar.gz"
        tar_path = os.path.join(EXPORTS_DIR, tar_name)
        
        # Export exam questions library
        from exam_exporter import export_exam_questions_as_library
        success = export_exam_questions_as_library(sections_data, tar_path)
        
        if success and os.path.exists(tar_path):
            return {"tar_file": f"/exports/{tar_name}"}
        else:
            raise Exception("Không tạo được file Exam Questions Library")
            
    except Exception as e:
        print(f"Error exporting exam questions library: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/export-exam-section/")
async def export_exam_section(
    section: str = Form(...),
    filename: Optional[str] = Query(None)
):
    """Export chỉ một section của đề thi"""
    try:
        # Parse section
        section_data = json.loads(section)
        
        # Create safe filename
        section_title = section_data.get("title", "section")
        safe_filename = "".join(c for c in (filename or section_title) if c.isalnum() or c in ('-', '_', '.'))
        if not safe_filename:
            safe_filename = "exam_section"
        
        # Create tar.gz file
        tar_name = f"{safe_filename}.tar.gz"
        tar_path = os.path.join(EXPORTS_DIR, tar_name)
        
        # Export exam section
        from exam_exporter import export_exam_section_only
        success = export_exam_section_only(section_data, tar_path)
        
        if success and os.path.exists(tar_path):
            return {"tar_file": f"/exports/{tar_name}"}
        else:
            raise Exception("Không tạo được file Exam Section")
            
    except Exception as e:
        print(f"Error exporting exam section: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/export-video-quiz/")
async def export_video_quiz(
    video_title: str = Form(...),
    video_url: str = Form(...),
    video_description: str = Form(""),
    questions: str = Form(...),
    filename: Optional[str] = Query(None)
):
    """Export video quiz as Open edX format"""
    try:
        # Parse questions
        questions_data = json.loads(questions)
        
        # Create video quiz data
        video_quiz_data = {
            "video_title": video_title,
            "video_url": video_url,
            "video_description": video_description,
            "questions": questions_data
        }
        
        # Create safe filename
        safe_filename = "".join(c for c in (filename or video_title) if c.isalnum() or c in ('-', '_', '.'))
        if not safe_filename:
            safe_filename = "video_quiz_export"
        
        # Create tar.gz file
        tar_name = f"{safe_filename}.tar.gz"
        tar_path = os.path.join(EXPORTS_DIR, tar_name)
        
        # Export video quiz
        success = export_video_quiz_to_tar(video_quiz_data, tar_path)
        
        if success and os.path.exists(tar_path):
            return {"tar_file": f"/exports/{tar_name}"}
        else:
            raise Exception("Không tạo được file Video Quiz")
            
    except Exception as e:
        print(f"Error exporting video quiz: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.host, port=config.port, debug=config.debug) 