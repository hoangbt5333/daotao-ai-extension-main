"""
Logging configuration
"""
import logging
import sys
from typing import Optional
from pathlib import Path
from app.config.settings import get_settings


def setup_logging(
    log_level: Optional[str] = None,
    log_file: Optional[str] = None,
    log_format: Optional[str] = None
) -> None:
    """
    Setup application logging
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (optional)
        log_format: Custom log format (optional)
    """
    settings = get_settings()
    
    # Default values
    if log_level is None:
        log_level = "DEBUG" if settings.debug else "INFO"
    
    if log_format is None:
        log_format = (
            "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
        )
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Add file handler if log_file is specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter(log_format))
        
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)
    
    # Set specific loggers
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    
    # Application logger
    app_logger = logging.getLogger("daotao_ai")
    app_logger.setLevel(getattr(logging, log_level.upper()))
    
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured with level: {log_level}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    return logging.getLogger(f"daotao_ai.{name}") 