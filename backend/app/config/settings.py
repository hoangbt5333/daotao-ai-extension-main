"""
Application settings configuration
"""
from typing import Optional, Dict, Any, List
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
import os
import json


class LLMSettings(BaseSettings):
    """LLM provider settings"""
    gemini_api_key: Optional[str] = Field(default=None, env="GEMINI_API_KEY")
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    deepseek_api_key: Optional[str] = Field(default=None, env="DEEPSEEK_API_KEY")
    default_provider: str = Field(default="openai", env="DEFAULT_LLM_PROVIDER")
    
    class Config:
        env_file = ".env"
        extra = "ignore"  # Ignore extra fields


class FileSettings(BaseSettings):
    """File handling settings"""
    upload_dir: str = Field(default="uploads", env="UPLOAD_DIR")
    export_dir: str = Field(default="exports", env="EXPORT_DIR")
    max_file_size: int = Field(default=50 * 1024 * 1024, env="MAX_FILE_SIZE")  # 50MB
    allowed_extensions: List[str] = Field(default=[".pdf", ".docx", ".txt"], env="ALLOWED_EXTENSIONS")
    
    @field_validator('allowed_extensions', mode='before')
    @classmethod
    def parse_allowed_extensions(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [".pdf", ".docx", ".txt"]
        return v
    
    class Config:
        env_file = ".env"
        extra = "ignore"  # Ignore extra fields


class Settings(BaseSettings):
    """Main application settings"""
    app_name: str = Field(default="Daotao AI Extension API", env="APP_NAME")
    version: str = Field(default="1.0.0", env="APP_VERSION")
    debug: bool = Field(default=False, env="DEBUG")
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    
    # CORS settings
    cors_origins: List[str] = Field(default=["http://localhost:3000"], env="CORS_ORIGINS")
    cors_credentials: bool = Field(default=True, env="CORS_CREDENTIALS")
    
    @field_validator('cors_origins', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return ["http://localhost:3000"]
        return v
    
    # LLM settings
    llm: LLMSettings = Field(default_factory=LLMSettings)
    
    # File settings
    file: FileSettings = Field(default_factory=FileSettings)
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get global settings instance (singleton pattern)"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def clear_settings_cache() -> None:
    """Clear the cached settings to force reload"""
    global _settings
    _settings = None


def get_llm_settings() -> LLMSettings:
    """Get LLM settings"""
    return get_settings().llm


def get_file_settings() -> FileSettings:
    """Get file settings"""
    return get_settings().file 