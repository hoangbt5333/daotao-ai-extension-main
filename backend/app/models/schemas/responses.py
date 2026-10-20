"""
Response schemas for API endpoints
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class BaseResponse(BaseModel):
    """Base response model"""
    success: bool = Field(..., description="Operation success status")
    message: Optional[str] = Field(None, description="Response message")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")


class ErrorResponse(BaseResponse):
    """Error response model"""
    success: bool = Field(default=False, description="Operation success status")
    error_code: Optional[str] = Field(None, description="Error code")
    details: Optional[Dict[str, Any]] = Field(None, description="Error details")


class AnalysisResponse(BaseResponse):
    """Response schema for text analysis"""
    success: bool = Field(default=True, description="Operation success status")
    data: Dict[str, Any] = Field(..., description="Analysis results")
    provider: Optional[str] = Field(None, description="LLM provider used")


class ExportResponse(BaseResponse):
    """Response schema for export operations"""
    success: bool = Field(default=True, description="Operation success status")
    tar_file: str = Field(..., description="Path to exported file")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    export_type: str = Field(..., description="Type of export")


class OutlineImportResponse(BaseResponse):
    """Response schema for outline import (Excel)"""
    success: bool = Field(default=True, description="Operation success status")
    outline: Dict[str, Any] = Field(..., description="Constructed outline")
    rows: List[Dict[str, Any]] = Field(..., description="Normalized rows for preview")
    warnings: List[str] = Field(default_factory=list, description="Warnings during import")


class UploadResponse(BaseResponse):
    """Response schema for file upload"""
    success: bool = Field(default=True, description="Operation success status")
    filename: str = Field(..., description="Uploaded file name")
    text_preview: str = Field(..., description="Preview of extracted text")
    full_text: str = Field(..., description="Full extracted text")


class ProviderResponse(BaseResponse):
    """Response schema for provider information"""
    success: bool = Field(default=True, description="Operation success status")
    available: Dict[str, bool] = Field(..., description="Available providers")
    default: Optional[str] = Field(None, description="Default provider")


class QuestionProcessingResponse(BaseResponse):
    """Response schema for question processing"""
    success: bool = Field(default=True, description="Operation success status")
    questions: List[Dict[str, Any]] = Field(..., description="Processed questions")
    mode: str = Field(..., description="Processing mode used")


class MappingResponse(BaseResponse):
    """Response schema for PDF mapping"""
    success: bool = Field(default=True, description="Operation success status")
    mapped_outline: Dict[str, Any] = Field(..., description="Mapped outline")
    mapped_count: int = Field(..., description="Number of files mapped")


class QuestionFilterResponse(BaseResponse):
    """Response schema for question filtering"""
    success: bool = Field(default=True, description="Operation success status")
    questions: List[Dict[str, Any]] = Field(..., description="Filtered questions")
    total_found: int = Field(..., description="Total questions found")
    filters_applied: Dict[str, Any] = Field(..., description="Filters that were applied")


class HealthCheckResponse(BaseResponse):
    """Response schema for health check"""
    success: bool = Field(default=True, description="Operation success status")
    status: str = Field(default="healthy", description="Service status")
    version: str = Field(..., description="Application version")
    uptime: Optional[float] = Field(None, description="Service uptime in seconds")
    dependencies: Dict[str, str] = Field(default={}, description="Dependency status")


class RootResponse(BaseResponse):
    """Response schema for root endpoint"""
    success: bool = Field(default=True, description="Operation success status")
    app_name: str = Field(..., description="Application name")
    version: str = Field(..., description="Application version")
    endpoints: Dict[str, str] = Field(..., description="Available endpoints") 