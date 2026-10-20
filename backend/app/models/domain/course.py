"""
Course domain models
"""
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum
from datetime import datetime


class ContentType(Enum):
    """Content type enumeration"""
    PDF = "pdf"
    VIDEO = "video"
    TEXT = "text"
    DOCX = "docx"
    HTML = "html"
    IMAGE = "image"


@dataclass
class Unit:
    """Course unit model"""
    title: str
    content_type: ContentType
    file_path: Optional[str] = None
    content: Optional[str] = None
    description: Optional[str] = None
    duration: Optional[int] = None  # in minutes
    order: int = 0
    
    def __post_init__(self):
        if isinstance(self.content_type, str):
            self.content_type = ContentType(self.content_type)


@dataclass
class Subsection:
    """Course subsection model"""
    title: str
    units: List[Unit] = field(default_factory=list)
    description: Optional[str] = None
    order: int = 0
    
    def add_unit(self, unit: Unit) -> None:
        """Add a unit to this subsection"""
        unit.order = len(self.units)
        self.units.append(unit)
    
    def get_units_by_type(self, content_type: ContentType) -> List[Unit]:
        """Get units by content type"""
        return [unit for unit in self.units if unit.content_type == content_type]


@dataclass
class Chapter:
    """Course chapter model"""
    title: str
    subsections: List[Subsection] = field(default_factory=list)
    description: Optional[str] = None
    order: int = 0
    
    def add_subsection(self, subsection: Subsection) -> None:
        """Add a subsection to this chapter"""
        subsection.order = len(self.subsections)
        self.subsections.append(subsection)
    
    def get_all_units(self) -> List[Unit]:
        """Get all units from all subsections"""
        units = []
        for subsection in self.subsections:
            units.extend(subsection.units)
        return units


@dataclass
class Course:
    """Course model"""
    title: str
    chapters: List[Chapter] = field(default_factory=list)
    organization: str = "SoDiTEC"
    course_code: str = "TDC01"
    description: Optional[str] = None
    language: str = "vi"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def add_chapter(self, chapter: Chapter) -> None:
        """Add a chapter to this course"""
        chapter.order = len(self.chapters)
        self.chapters.append(chapter)
    
    def get_all_units(self) -> List[Unit]:
        """Get all units from all chapters"""
        units = []
        for chapter in self.chapters:
            units.extend(chapter.get_all_units())
        return units
    
    def get_units_by_type(self, content_type: ContentType) -> List[Unit]:
        """Get all units by content type"""
        return [unit for unit in self.get_all_units() if unit.content_type == content_type]
    
    def get_total_duration(self) -> int:
        """Get total course duration in minutes"""
        return sum(unit.duration or 0 for unit in self.get_all_units())
    
    def validate(self) -> bool:
        """Validate course structure"""
        if not self.title:
            return False
        
        if not self.chapters:
            return False
        
        for chapter in self.chapters:
            if not chapter.title or not chapter.subsections:
                return False
            
            for subsection in chapter.subsections:
                if not subsection.title or not subsection.units:
                    return False
                
                for unit in subsection.units:
                    if not unit.title:
                        return False
        
        return True 