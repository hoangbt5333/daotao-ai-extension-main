"""
File upload handling service
"""
import os
import tempfile
from typing import List, Optional
from fastapi import UploadFile
from app.core.logging import get_logger
from app.core.exceptions import FileProcessingError
from app.config.settings import get_file_settings


class FileUploader:
    """Service for handling file uploads"""
    
    def __init__(self):
        self.logger = get_logger("file.uploader")
        self.settings = get_file_settings()
    
    def save_uploaded_file(self, file: UploadFile, destination_dir: Optional[str] = None) -> str:
        """
        Save an uploaded file to disk
        
        Args:
            file: Uploaded file
            destination_dir: Directory to save file (optional, uses default upload dir)
            
        Returns:
            Path to saved file
        """
        try:
            # Validate file
            if not file.filename:
                raise FileProcessingError("No filename provided")
            
            if not self._validate_file_type(file.filename):
                raise FileProcessingError(f"Unsupported file type: {file.filename}")
            
            if not self._validate_file_size(file):
                raise FileProcessingError(f"File too large: {file.filename}")
            
            # Determine destination directory
            if destination_dir is None:
                destination_dir = self.settings.upload_dir
            
            # Create destination directory
            os.makedirs(destination_dir, exist_ok=True)
            
            # Generate safe filename
            safe_filename = self._generate_safe_filename(file.filename)
            file_path = os.path.join(destination_dir, safe_filename)
            
            # Save file
            content = file.file.read()
            with open(file_path, "wb") as f:
                f.write(content)
            
            file_size = len(content)
            self.logger.info(f"Saved uploaded file: {file_path} ({file_size} bytes)")
            
            return file_path
            
        except Exception as e:
            self.logger.error(f"Error saving uploaded file {file.filename}: {e}")
            raise FileProcessingError(f"Failed to save uploaded file: {str(e)}")
    
    def save_multiple_files(self, files: List[UploadFile], destination_dir: Optional[str] = None) -> List[str]:
        """
        Save multiple uploaded files
        
        Args:
            files: List of uploaded files
            destination_dir: Directory to save files (optional)
            
        Returns:
            List of paths to saved files
        """
        saved_files = []
        
        for file in files:
            try:
                file_path = self.save_uploaded_file(file, destination_dir)
                saved_files.append(file_path)
            except Exception as e:
                self.logger.error(f"Failed to save file {file.filename}: {e}")
                # Continue with other files
                continue
        
        return saved_files
    
    def create_temp_file(self, file: UploadFile) -> str:
        """
        Create a temporary file from uploaded file
        
        Args:
            file: Uploaded file
            
        Returns:
            Path to temporary file
        """
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
                content = file.file.read()
                temp_file.write(content)
                temp_file_path = temp_file.name
            
            self.logger.info(f"Created temp file: {temp_file_path}")
            return temp_file_path
            
        except Exception as e:
            self.logger.error(f"Error creating temp file for {file.filename}: {e}")
            raise FileProcessingError(f"Failed to create temp file: {str(e)}")
    
    def _validate_file_type(self, filename: str) -> bool:
        """Validate if file type is supported"""
        if not filename:
            return False
        
        file_ext = os.path.splitext(filename)[1].lower()
        return file_ext in self.settings.allowed_extensions
    
    def _validate_file_size(self, file: UploadFile) -> bool:
        """Validate file size"""
        try:
            # Read file content to get size
            content = file.file.read()
            file.file.seek(0)  # Reset file pointer
            
            return len(content) <= self.settings.max_file_size
            
        except Exception as e:
            self.logger.error(f"Error validating file size: {e}")
            return False
    
    def _generate_safe_filename(self, filename: str) -> str:
        """Generate a safe filename"""
        import re
        from datetime import datetime
        
        # Remove or replace unsafe characters
        safe_name = re.sub(r'[<>:"/\\|?*]', '_', filename)
        
        # Add timestamp to avoid conflicts
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name, ext = os.path.splitext(safe_name)
        
        return f"{name}_{timestamp}{ext}"
    
    def get_file_info(self, file: UploadFile) -> dict:
        """Get information about uploaded file"""
        try:
            content = file.file.read()
            file.file.seek(0)  # Reset file pointer
            
            return {
                "filename": file.filename,
                "content_type": file.content_type,
                "size": len(content),
                "is_valid_type": self._validate_file_type(file.filename),
                "is_valid_size": len(content) <= self.settings.max_file_size
            }
        except Exception as e:
            self.logger.error(f"Error getting file info: {e}")
            return {
                "filename": file.filename,
                "content_type": file.content_type,
                "size": 0,
                "is_valid_type": False,
                "is_valid_size": False
            }
    
    def cleanup_temp_file(self, file_path: str) -> bool:
        """Clean up temporary file"""
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
                self.logger.info(f"Cleaned up temp file: {file_path}")
                return True
            return True
        except Exception as e:
            self.logger.error(f"Error cleaning up temp file {file_path}: {e}")
            return False


# Global uploader instance
file_uploader = FileUploader() 