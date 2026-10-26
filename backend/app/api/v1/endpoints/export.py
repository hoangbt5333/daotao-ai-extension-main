"""
Export endpoints
"""
from fastapi import APIRouter, Form, Query, File, UploadFile, Depends
from typing import List, Optional
import json
import tempfile
import os
import shutil
from app.models.schemas.responses import ExportResponse
from app.core.exceptions import ExportError
from app.config.settings import get_settings
from app.services.export.base import export_service

router = APIRouter()


@router.post("/", response_model=ExportResponse)
async def export_openedx(
    files: List[UploadFile] = File([]),
    outline: str = Form(...),
    questions: str = Form(...),
    filename: Optional[str] = Query(None)
):
    """Export outline and questions to Open edX format"""
    try:
        settings = get_settings()
        
        # Parse input data
        outline_data = json.loads(outline)
        questions_data = json.loads(questions)
        
        # Create safe filename
        safe_filename = "".join(c for c in (filename or "course_export") if c.isalnum() or c in ('-', '_', '.'))
        if not safe_filename:
            safe_filename = "course_export"
        
        # Create temporary directory for export
        temp_dir = tempfile.mkdtemp()
        tar_name = f"{safe_filename}.tar.gz"
        tar_path = os.path.join(settings.file.export_dir, tar_name)
        
        # Save uploaded asset files (PDF, MP3, etc.) to temporary paths
        allowed_extensions = ('.pdf', '.mp3', '.ogg', '.wav')
        uploaded_asset_paths = []
        for file in files:
            if file.filename and file.filename.lower().endswith(allowed_extensions):
                temp_file_path = os.path.join(temp_dir, file.filename)
                with open(temp_file_path, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)
                uploaded_asset_paths.append(temp_file_path)
        
        try:
            # Prepare data for export
            export_data = {
                "outline": outline_data.get('outline', []) if isinstance(outline_data, dict) else outline_data,
                "questions": questions_data.get('questions', []) if isinstance(questions_data, dict) else questions_data,
                "uploaded_pdfs": uploaded_asset_paths,
                "uploaded_assets": uploaded_asset_paths
            }
            
            # Export using service
            success = export_service.export("openedx", export_data, tar_path)
            
            if success and os.path.exists(tar_path):
                return ExportResponse(
                    success=True,
                    tar_file=f"/exports/{tar_name}",
                    export_type="openedx",
                    message="Course exported successfully"
                )
            else:
                raise ExportError("Failed to create export file")
            
        finally:
            # Clean up temporary directory
            shutil.rmtree(temp_dir, ignore_errors=True)
            
    except json.JSONDecodeError as e:
        return ExportResponse(
            success=False,
            tar_file="",
            export_type="openedx",
            message=f"Invalid JSON data: {str(e)}"
        )
    except Exception as e:
        return ExportResponse(
            success=False,
            tar_file="",
            export_type="openedx",
            message=f"Export failed: {str(e)}"
        )


@router.post("/library", response_model=ExportResponse)
async def export_library(
    questions: str = Form(...),
    library_name: str = Form(...),
    org: str = Form("SoDiTEC"),
    library_code: str = Form("LIB001"),
    start_time: str = Form(None),
    filename: Optional[str] = Query(None),
    question_type: str = Form("multiple_choice")
):
    """Export questions as Library format"""
    try:
        settings = get_settings()
        
        # Parse questions
        questions_data = json.loads(questions)
        questions_list = questions_data.get("questions", [])
        
        # Create safe filename
        safe_filename = "".join(c for c in (filename or library_name) if c.isalnum() or c in ('-', '_', '.'))
        if not safe_filename:
            safe_filename = "library_export"
        
        # Create tar.gz file
        tar_name = f"{safe_filename}.tar.gz"
        tar_path = os.path.join(settings.file.export_dir, tar_name)
        
        # Process start_time
        if start_time:
            if not (start_time.startswith('"') and start_time.endswith('"')):
                start_time = f'"{start_time.strip()}"'
        else:
            start_time = '"2030-01-01T00:00:00Z"'
        
        # Export using service
        export_data = {
            "questions": questions_list,
            "library_name": library_name,
            "org": org,
            "library_code": library_code,
            "start_time": start_time,
            "question_type": question_type
        }
        
        success = export_service.export("library", export_data, tar_path)
        
        if success and os.path.exists(tar_path):
            return ExportResponse(
                success=True,
                tar_file=f"/exports/{tar_name}",
                export_type="library",
                message="Library exported successfully"
            )
        else:
            raise ExportError("Failed to create library export file")
        
    except json.JSONDecodeError as e:
        return ExportResponse(
            success=False,
            tar_file="",
            export_type="library",
            message=f"Invalid JSON data: {str(e)}"
        )
    except Exception as e:
        return ExportResponse(
            success=False,
            tar_file="",
            export_type="library",
            message=f"Library export failed: {str(e)}"
        )


@router.post("/exam", response_model=ExportResponse)
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
        settings = get_settings()
        
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
        tar_path = os.path.join(settings.file.export_dir, tar_name)
        
        # Export using service
        success = export_service.export("exam", exam_data, tar_path)
        
        if success and os.path.exists(tar_path):
            return ExportResponse(
                success=True,
                tar_file=f"/exports/{tar_name}",
                export_type="exam",
                message="Exam exported successfully"
            )
        else:
            raise ExportError("Failed to create exam export file")
            
    except json.JSONDecodeError as e:
        return ExportResponse(
            success=False,
            tar_file="",
            export_type="exam",
            message=f"Invalid JSON data: {str(e)}"
        )
    except Exception as e:
        return ExportResponse(
            success=False,
            tar_file="",
            export_type="exam",
            message=f"Exam export failed: {str(e)}"
        )


@router.post("/exam-subsection", response_model=ExportResponse)
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
        settings = get_settings()
        
        # Parse sections
        sections_data = json.loads(sections)
        
        # Create exam data
        exam_data = {
            "exam_name": exam_name,
            "exam_description": exam_description,
            "total_time": total_time,
            "is_timed": is_timed,
            "sections": sections_data,
            "export_type": "subsection"
        }
        
        # Create safe filename
        safe_filename = "".join(c for c in (filename or exam_name) if c.isalnum() or c in ('-', '_', '.'))
        if not safe_filename:
            safe_filename = "exam_subsection_export"
        
        # Create tar.gz file
        tar_name = f"{safe_filename}.tar.gz"
        tar_path = os.path.join(settings.file.export_dir, tar_name)
        
        # Export using service
        success = export_service.export("exam", exam_data, tar_path)
        
        if success and os.path.exists(tar_path):
            return ExportResponse(
                success=True,
                tar_file=f"/exports/{tar_name}",
                export_type="exam_subsection",
                message="Exam subsection exported successfully"
            )
        else:
            raise ExportError("Failed to create exam subsection export file")
            
    except json.JSONDecodeError as e:
        return ExportResponse(
            success=False,
            tar_file="",
            export_type="exam_subsection",
            message=f"Invalid JSON data: {str(e)}"
        )
    except Exception as e:
        return ExportResponse(
            success=False,
            tar_file="",
            export_type="exam_subsection",
            message=f"Exam subsection export failed: {str(e)}"
        )


@router.post("/exam-questions-library", response_model=ExportResponse)
async def export_exam_questions_library(
    sections: str = Form(...),
    filename: Optional[str] = Query(None)
):
    """Export câu hỏi từ đề thi dạng Library"""
    try:
        settings = get_settings()
        
        # Parse sections
        sections_data = json.loads(sections)
        
        # Create safe filename
        safe_filename = "".join(c for c in (filename or "exam_questions_library") if c.isalnum() or c in ('-', '_', '.'))
        if not safe_filename:
            safe_filename = "exam_questions_library"
        
        # Create tar.gz file
        tar_name = f"{safe_filename}.tar.gz"
        tar_path = os.path.join(settings.file.export_dir, tar_name)
        
        # Export using service
        export_data = {
            "sections": sections_data,
            "export_type": "questions_library"
        }
        
        success = export_service.export("exam", export_data, tar_path)
        
        if success and os.path.exists(tar_path):
            return ExportResponse(
                success=True,
                tar_file=f"/exports/{tar_name}",
                export_type="exam_questions_library",
                message="Exam questions library exported successfully"
            )
        else:
            raise ExportError("Failed to create exam questions library export file")
            
    except json.JSONDecodeError as e:
        return ExportResponse(
            success=False,
            tar_file="",
            export_type="exam_questions_library",
            message=f"Invalid JSON data: {str(e)}"
        )
    except Exception as e:
        return ExportResponse(
            success=False,
            tar_file="",
            export_type="exam_questions_library",
            message=f"Exam questions library export failed: {str(e)}"
        )


@router.post("/exam-section", response_model=ExportResponse)
async def export_exam_section(
    section: str = Form(...),
    filename: Optional[str] = Query(None)
):
    """Export chỉ một section của đề thi"""
    try:
        settings = get_settings()
        
        # Parse section
        section_data = json.loads(section)
        
        # Create safe filename
        section_title = section_data.get("title", "section")
        safe_filename = "".join(c for c in (filename or section_title) if c.isalnum() or c in ('-', '_', '.'))
        if not safe_filename:
            safe_filename = "exam_section"
        
        # Create tar.gz file
        tar_name = f"{safe_filename}.tar.gz"
        tar_path = os.path.join(settings.file.export_dir, tar_name)
        
        # Export using service
        export_data = {
            "section": section_data,
            "export_type": "section_only"
        }
        
        success = export_service.export("exam", export_data, tar_path)
        
        if success and os.path.exists(tar_path):
            return ExportResponse(
                success=True,
                tar_file=f"/exports/{tar_name}",
                export_type="exam_section",
                message="Exam section exported successfully"
            )
        else:
            raise ExportError("Failed to create exam section export file")
            
    except json.JSONDecodeError as e:
        return ExportResponse(
            success=False,
            tar_file="",
            export_type="exam_section",
            message=f"Invalid JSON data: {str(e)}"
        )
    except Exception as e:
        return ExportResponse(
            success=False,
            tar_file="",
            export_type="exam_section",
            message=f"Exam section export failed: {str(e)}"
        )


@router.post("/video-quiz", response_model=ExportResponse)
async def export_video_quiz(
    video_title: str = Form(...),
    video_url: str = Form(...),
    video_description: str = Form(""),
    questions: str = Form(...),
    filename: Optional[str] = Query(None)
):
    """Export video quiz as Open edX format"""
    try:
        settings = get_settings()
        
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
        tar_path = os.path.join(settings.file.export_dir, tar_name)
        
        # Export using service
        success = export_service.export("video_quiz", video_quiz_data, tar_path)
        
        if success and os.path.exists(tar_path):
            return ExportResponse(
                success=True,
                tar_file=f"/exports/{tar_name}",
                export_type="video_quiz",
                message="Video quiz exported successfully"
            )
        else:
            raise ExportError("Failed to create video quiz export file")
            
    except json.JSONDecodeError as e:
        return ExportResponse(
            success=False,
            tar_file="",
            export_type="video_quiz",
            message=f"Invalid JSON data: {str(e)}"
        )
    except Exception as e:
        return ExportResponse(
            success=False,
            tar_file="",
            export_type="video_quiz",
            message=f"Video quiz export failed: {str(e)}"
        ) 