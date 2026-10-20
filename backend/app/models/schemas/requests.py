"""
Request schemas for API endpoints
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from app.models.domain.question import QuestionType


class AnalysisRequest(BaseModel):
    """Request schema for text analysis"""
    text: str = Field(..., min_length=1, description="Text to analyze")
    provider: Optional[str] = Field(None, description="LLM provider to use")
    
    @validator('text')
    def validate_text(cls, v):
        if not v.strip():
            raise ValueError('Text cannot be empty')
        return v.strip()


class ExportRequest(BaseModel):
    """Request schema for course export"""
    outline: List[Dict[str, Any]] = Field(..., description="Course outline")
    questions: List[Dict[str, Any]] = Field(default=[], description="Course questions")
    filename: Optional[str] = Field(None, description="Export filename")
    export_type: str = Field(default="openedx", description="Export type")
    
    @validator('filename')
    def validate_filename(cls, v):
        if v is not None:
            # Remove invalid characters
            import re
            v = re.sub(r'[<>:"/\\|?*]', '_', v)
            if not v.strip():
                v = "course_export"
        return v


class UploadRequest(BaseModel):
    """Request schema for file upload"""
    file_type: Optional[str] = Field(None, description="Expected file type")
    max_size: Optional[int] = Field(None, description="Maximum file size in bytes")


class QuestionProcessRequest(BaseModel):
    """Request schema for question processing"""
    questions_text: str = Field(..., description="Raw questions text")
    user_tags: List[str] = Field(default=[], description="User provided tags")
    tags_explanation: Optional[str] = Field(None, description="Tags explanation")
    mode: Optional[str] = Field("llm", description="Processing mode")
    user_format: Optional[str] = Field(None, description="User format specification")
    provider: Optional[str] = Field(None, description="LLM provider to use")
    
    @validator('questions_text')
    def validate_questions_text(cls, v):
        if not v.strip():
            raise ValueError('Questions text cannot be empty')
        return v.strip()


class LibraryExportRequest(BaseModel):
    """Request schema for library export"""
    questions: List[Dict[str, Any]] = Field(..., description="Questions to export")
    library_name: str = Field(..., description="Library name")
    org: str = Field(default="SoDiTEC", description="Organization")
    library_code: str = Field(default="LIB001", description="Library code")
    start_time: Optional[str] = Field(None, description="Start time")
    filename: Optional[str] = Field(None, description="Export filename")


class ExamExportRequest(BaseModel):
    """Request schema for exam export"""
    exam_name: str = Field(..., description="Exam name")
    exam_description: Optional[str] = Field(None, description="Exam description")
    total_time: int = Field(default=90, description="Total time in minutes")
    is_timed: bool = Field(default=True, description="Is timed exam")
    sections: List[Dict[str, Any]] = Field(..., description="Exam sections")
    filename: Optional[str] = Field(None, description="Export filename")


class VideoQuizExportRequest(BaseModel):
    """Request schema for video quiz export"""
    video_title: str = Field(..., description="Video title")
    video_url: str = Field(..., description="Video URL")
    video_description: Optional[str] = Field(None, description="Video description")
    questions: List[Dict[str, Any]] = Field(..., description="Video questions")
    filename: Optional[str] = Field(None, description="Export filename")


class PDFMappingRequest(BaseModel):
    """Request schema for PDF mapping"""
    files: List[str] = Field(..., description="PDF file names")
    outline: Dict[str, Any] = Field(..., description="Course outline")
    
    @validator('files')
    def validate_files(cls, v):
        if not v:
            raise ValueError('At least one file must be provided')
        return v


class QuestionFilterRequest(BaseModel):
    """Request schema for question filtering"""
    tags: List[str] = Field(default=[], description="Tags to filter by")
    count: int = Field(default=5, ge=1, le=100, description="Number of questions to return")
    difficulty: Optional[str] = Field(None, description="Difficulty level")
    question_type: Optional[QuestionType] = Field(None, description="Question type") 