import os
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

@dataclass
class LLMConfig:
    """Configuration for LLM providers"""
    gemini_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    deepseek_api_key: Optional[str] = None
    default_provider: str = "openai"

@dataclass
class AppConfig:
    """Main application configuration"""
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    llm: LLMConfig = None

def load_config() -> AppConfig:
    """Load configuration from environment variables"""
    llm_config = LLMConfig(
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        deepseek_api_key=os.getenv("DEEPSEEK_API_KEY"),
        default_provider=os.getenv("DEFAULT_LLM_PROVIDER", "openai")
    )
    
    return AppConfig(
        debug=os.getenv("DEBUG", "false").lower() == "true",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        llm=llm_config
    )

# Global config instance
config = load_config() 