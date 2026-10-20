"""
Custom exceptions for the application
"""
from fastapi import HTTPException
from typing import Optional, Any, Dict


class BaseAppException(HTTPException):
    """Base exception for application errors"""
    
    def __init__(
        self,
        status_code: int,
        detail: str,
        error_code: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None
    ):
        super().__init__(status_code=status_code, detail=detail)
        self.error_code = error_code
        self.extra_data = extra_data or {}


class ValidationError(BaseAppException):
    """Raised when data validation fails"""
    
    def __init__(self, detail: str, field: Optional[str] = None):
        super().__init__(
            status_code=400,
            detail=detail,
            error_code="VALIDATION_ERROR",
            extra_data={"field": field} if field else {}
        )


class FileProcessingError(BaseAppException):
    """Raised when file processing fails"""
    
    def __init__(self, detail: str, file_name: Optional[str] = None):
        super().__init__(
            status_code=400,
            detail=detail,
            error_code="FILE_PROCESSING_ERROR",
            extra_data={"file_name": file_name} if file_name else {}
        )


class LLMServiceError(BaseAppException):
    """Raised when LLM service fails"""
    
    def __init__(self, detail: str, provider: Optional[str] = None):
        super().__init__(
            status_code=503,
            detail=detail,
            error_code="LLM_SERVICE_ERROR",
            extra_data={"provider": provider} if provider else {}
        )


class ExportError(BaseAppException):
    """Raised when export operation fails"""
    
    def __init__(self, detail: str, export_type: Optional[str] = None):
        super().__init__(
            status_code=500,
            detail=detail,
            error_code="EXPORT_ERROR",
            extra_data={"export_type": export_type} if export_type else {}
        )


class ConfigurationError(BaseAppException):
    """Raised when configuration is invalid"""
    
    def __init__(self, detail: str, config_key: Optional[str] = None):
        super().__init__(
            status_code=500,
            detail=detail,
            error_code="CONFIGURATION_ERROR",
            extra_data={"config_key": config_key} if config_key else {}
        )


class ResourceNotFoundError(BaseAppException):
    """Raised when a resource is not found"""
    
    def __init__(self, detail: str, resource_type: Optional[str] = None):
        super().__init__(
            status_code=404,
            detail=detail,
            error_code="RESOURCE_NOT_FOUND",
            extra_data={"resource_type": resource_type} if resource_type else {}
        ) 