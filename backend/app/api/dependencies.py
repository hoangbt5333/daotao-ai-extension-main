"""
API dependencies
"""
from fastapi import Depends
from app.services.llm.base import LLMService
from app.services.file.extractor import file_extractor
from app.services.file.uploader import file_uploader
from app.services.file.packager import file_packager
from app.config.settings import get_settings


def get_llm_service() -> LLMService:
    """Get LLM service instance"""
    return LLMService()


def get_file_extractor():
    """Get file extractor instance"""
    return file_extractor


def get_file_uploader():
    """Get file uploader instance"""
    return file_uploader


def get_file_packager():
    """Get file packager instance"""
    return file_packager


def get_settings_dependency():
    """Get settings instance"""
    return get_settings() 