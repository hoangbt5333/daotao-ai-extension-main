"""
File text extraction service
"""
import os
import tempfile
from typing import Optional
from fastapi import UploadFile
from app.core.logging import get_logger
from app.core.exceptions import FileProcessingError
from app.config.settings import get_file_settings


class FileExtractor:
    """Service for extracting text from various file formats"""
    
    def __init__(self):
        self.logger = get_logger("file.extractor")
        self.settings = get_file_settings()
    
    def extract_text(self, file_path: str) -> str:
        """Extract text from file - alias for extract_text_from_file"""
        return self.extract_text_from_file(file_path)
    
    def extract_text_from_file(self, file_path: str) -> str:
        """Extract text from file based on file extension"""
        if not os.path.exists(file_path):
            raise FileProcessingError(f"File not found: {file_path}")
        
        file_ext = os.path.splitext(file_path)[1].lower()
        
        try:
            if file_ext == ".pdf":
                return self._extract_from_pdf(file_path)
            elif file_ext == ".docx":
                return self._extract_from_docx(file_path)
            elif file_ext == ".txt":
                return self._extract_from_txt(file_path)
            else:
                raise FileProcessingError(f"Unsupported file type: {file_ext}")
        except Exception as e:
            self.logger.error(f"Error extracting text from {file_path}: {e}")
            raise FileProcessingError(f"Failed to extract text: {str(e)}")
    
    def extract_text_from_upload(self, file: UploadFile) -> str:
        """Extract text from uploaded file"""
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
                content = file.file.read()
                temp_file.write(content)
                temp_file_path = temp_file.name
            
            # Extract text
            text = self.extract_text_from_file(temp_file_path)
            
            # Clean up temp file
            os.unlink(temp_file_path)
            
            return text
            
        except Exception as e:
            self.logger.error(f"Error extracting text from uploaded file {file.filename}: {e}")
            raise FileProcessingError(f"Failed to extract text from uploaded file: {str(e)}")
    
    def _extract_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF file"""
        try:
            import pdfplumber
            
            text = ""
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            
            self.logger.info(f"Successfully extracted {len(text)} characters from PDF")
            return text.strip()
            
        except ImportError:
            raise FileProcessingError("pdfplumber library not installed")
        except Exception as e:
            raise FileProcessingError(f"Failed to extract text from PDF: {str(e)}")
    
    def _extract_from_docx(self, file_path: str) -> str:
        """Extract text from DOCX file"""
        try:
            import docx
            
            doc = docx.Document(file_path)
            text = "\n".join([para.text for para in doc.paragraphs])
            
            self.logger.info(f"Successfully extracted {len(text)} characters from DOCX")
            return text.strip()
            
        except ImportError:
            raise FileProcessingError("python-docx library not installed")
        except Exception as e:
            raise FileProcessingError(f"Failed to extract text from DOCX: {str(e)}")
    
    def _extract_from_txt(self, file_path: str) -> str:
        """Extract text from TXT file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            self.logger.info(f"Successfully extracted {len(text)} characters from TXT")
            return text.strip()
            
        except UnicodeDecodeError:
            # Try with different encoding
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    text = f.read()
                return text.strip()
            except Exception as e:
                raise FileProcessingError(f"Failed to read TXT file with any encoding: {str(e)}")
        except Exception as e:
            raise FileProcessingError(f"Failed to extract text from TXT: {str(e)}")
    
    def validate_file_type(self, filename: str) -> bool:
        """Validate if file type is supported"""
        if not filename:
            return False
        
        file_ext = os.path.splitext(filename)[1].lower()
        return file_ext in self.settings.allowed_extensions
    
    def get_supported_extensions(self) -> list:
        """Get list of supported file extensions"""
        return self.settings.allowed_extensions.copy()


# Global extractor instance
file_extractor = FileExtractor() 