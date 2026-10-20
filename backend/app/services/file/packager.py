"""
File packaging service for creating tar.gz files
"""
import os
import tarfile
import shutil
import tempfile
from typing import Optional
from pathlib import Path
from app.core.logging import get_logger
from app.core.exceptions import FileProcessingError
from app.config.settings import get_file_settings


class FilePackager:
    """Service for creating tar.gz packages"""
    
    def __init__(self):
        self.logger = get_logger("file.packager")
        self.settings = get_file_settings()
    
    def create_tarfile(self, output_path: str, source_dir: str) -> bool:
        """
        Create a tar.gz file from the source directory
        
        Args:
            output_path: Path to the output .tar.gz file
            source_dir: Directory containing the files to package
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure output directory exists
            output_dir = os.path.dirname(output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            
            self.logger.info(f"Creating tar.gz file: {output_path}")
            
            with tarfile.open(output_path, "w:gz") as tar:
                # Add all files and directories from source_dir
                for root, dirs, files in os.walk(source_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        # Calculate the arcname (path within the tar file)
                        arcname = os.path.relpath(file_path, source_dir)
                        tar.add(file_path, arcname=arcname)
            
            # Verify file was created
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                self.logger.info(f"Successfully created {output_path} ({file_size} bytes)")
                return True
            else:
                self.logger.error(f"Tar file was not created: {output_path}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error creating tar file: {e}")
            return False
    
    def create_tarfile_from_files(self, output_path: str, files: list, base_dir: str = "") -> bool:
        """
        Create a tar.gz file from a list of files
        
        Args:
            output_path: Path to the output .tar.gz file
            files: List of file paths to include
            base_dir: Base directory for relative paths
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure output directory exists
            output_dir = os.path.dirname(output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            
            self.logger.info(f"Creating tar.gz file from {len(files)} files: {output_path}")
            
            with tarfile.open(output_path, "w:gz") as tar:
                for file_path in files:
                    if os.path.exists(file_path):
                        # Calculate arcname relative to base_dir
                        if base_dir:
                            arcname = os.path.relpath(file_path, base_dir)
                        else:
                            arcname = os.path.basename(file_path)
                        
                        tar.add(file_path, arcname=arcname)
                    else:
                        self.logger.warning(f"File not found: {file_path}")
            
            # Verify file was created
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                self.logger.info(f"Successfully created {output_path} ({file_size} bytes)")
                return True
            else:
                self.logger.error(f"Tar file was not created: {output_path}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error creating tar file from files: {e}")
            return False
    
    def extract_tarfile(self, tar_path: str, extract_dir: str) -> bool:
        """
        Extract a tar.gz file to a directory
        
        Args:
            tar_path: Path to the .tar.gz file
            extract_dir: Directory to extract to
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not os.path.exists(tar_path):
                self.logger.error(f"Tar file not found: {tar_path}")
                return False
            
            # Create extract directory
            os.makedirs(extract_dir, exist_ok=True)
            
            self.logger.info(f"Extracting {tar_path} to {extract_dir}")
            
            with tarfile.open(tar_path, "r:gz") as tar:
                tar.extractall(extract_dir)
            
            self.logger.info(f"Successfully extracted {tar_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error extracting tar file: {e}")
            return False
    
    def cleanup_temp_directory(self, temp_dir: str) -> bool:
        """
        Clean up temporary directory
        
        Args:
            temp_dir: Path to temporary directory
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                self.logger.info(f"Cleaned up temporary directory: {temp_dir}")
                return True
            return True
            
        except Exception as e:
            self.logger.error(f"Error cleaning up directory {temp_dir}: {e}")
            return False
    
    def get_file_size(self, file_path: str) -> Optional[int]:
        """Get file size in bytes"""
        try:
            if os.path.exists(file_path):
                return os.path.getsize(file_path)
            return None
        except Exception as e:
            self.logger.error(f"Error getting file size for {file_path}: {e}")
            return None
    
    def validate_tarfile(self, tar_path: str) -> bool:
        """
        Validate that a tar.gz file is valid and can be extracted
        
        Args:
            tar_path: Path to the .tar.gz file
            
        Returns:
            True if valid, False otherwise
        """
        try:
            if not os.path.exists(tar_path):
                return False
            
            with tarfile.open(tar_path, "r:gz") as tar:
                # Try to get member list to validate
                members = tar.getmembers()
                return len(members) > 0
                
        except Exception as e:
            self.logger.error(f"Error validating tar file {tar_path}: {e}")
            return False


# Global packager instance
file_packager = FilePackager() 