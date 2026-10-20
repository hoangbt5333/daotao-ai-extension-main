"""
Base export service and interface
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from app.core.logging import get_logger
from app.core.exceptions import ExportError
from app.models.domain.course import Course
from app.models.domain.question import Question, QuestionBank


class Exporter(ABC):
    """Abstract base class for exporters following SOLID principles"""
    
    def __init__(self, exporter_name: str):
        self.exporter_name = exporter_name
        self.logger = get_logger(f"export.{exporter_name}")
    
    @abstractmethod
    def export(self, data: Dict[str, Any], output_path: str) -> bool:
        """Export data to specified format"""
        pass
    
    @abstractmethod
    def validate_data(self, data: Dict[str, Any]) -> bool:
        """Validate export data"""
        pass
    
    def get_export_info(self) -> Dict[str, Any]:
        """Get information about the exporter"""
        return {
            "name": self.exporter_name,
            "supported_formats": self.get_supported_formats()
        }
    
    @abstractmethod
    def get_supported_formats(self) -> List[str]:
        """Get list of supported export formats"""
        pass


class ExportService:
    """Service class for managing exporters following SOLID principles"""
    
    def __init__(self):
        self.exporters: Dict[str, Exporter] = {}
        self.logger = get_logger("export.service")
        self._initialize_exporters()
    
    def _initialize_exporters(self) -> None:
        """Initialize available exporters"""
        # Import exporters here to avoid circular imports
        from .openedx import OpenEdXExporter
        from .library import LibraryExporter
        from .exam import ExamExporter
        from .video_quiz import VideoQuizExporter
        
        # Initialize exporters
        self.exporters['openedx'] = OpenEdXExporter()
        self.exporters['library'] = LibraryExporter()
        self.exporters['exam'] = ExamExporter()
        self.exporters['video_quiz'] = VideoQuizExporter()
        
        self.logger.info(f"Initialized {len(self.exporters)} exporters")
    
    def get_available_exporters(self) -> Dict[str, Dict[str, Any]]:
        """Get list of available exporters with their info"""
        return {
            name: exporter.get_export_info()
            for name, exporter in self.exporters.items()
        }
    
    def export(self, export_type: str, data: Dict[str, Any], output_path: str) -> bool:
        """
        Export data using specified exporter
        
        Args:
            export_type: Type of export (openedx, library, exam, video_quiz)
            data: Data to export
            output_path: Output file path
            
        Returns:
            True if successful, False otherwise
        """
        if export_type not in self.exporters:
            self.logger.error(f"Unknown export type: {export_type}")
            raise ExportError(f"Unknown export type: {export_type}")
        
        exporter = self.exporters[export_type]
        
        try:
            # Validate data
            if not exporter.validate_data(data):
                raise ExportError(f"Invalid data for {export_type} export")
            
            # Perform export
            self.logger.info(f"Starting {export_type} export to {output_path}")
            result = exporter.export(data, output_path)
            
            if result:
                self.logger.info(f"Successfully exported {export_type} to {output_path}")
            else:
                self.logger.error(f"Failed to export {export_type}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error during {export_type} export: {e}")
            raise ExportError(f"Export failed: {str(e)}", export_type)
    
    def get_exporter(self, export_type: str) -> Optional[Exporter]:
        """Get specific exporter instance"""
        return self.exporters.get(export_type)


# Global export service instance
export_service = ExportService() 