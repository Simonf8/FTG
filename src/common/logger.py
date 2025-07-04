"""
Logging configuration and utilities
"""

import logging
import sys
from typing import Optional
from pathlib import Path
from loguru import logger as loguru_logger


class InterceptHandler(logging.Handler):
    """
    Intercept standard logging messages and redirect them to loguru
    """
    
    def emit(self, record):
        # Get corresponding Loguru level if it exists
        try:
            level = loguru_logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        loguru_logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logger(
    level: str = "INFO",
    log_file: Optional[str] = None,
    rotation: str = "10 MB",
    retention: str = "30 days",
    format_string: Optional[str] = None
) -> None:
    """
    Setup loguru logger with custom configuration
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (optional)
        rotation: Log rotation policy
        retention: Log retention policy
        format_string: Custom format string
    """
    # Remove default logger
    loguru_logger.remove()
    
    # Default format
    if format_string is None:
        format_string = (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )
    
    # Console handler
    loguru_logger.add(
        sys.stdout,
        level=level,
        format=format_string,
        colorize=True,
        backtrace=True,
        diagnose=True
    )
    
    # File handler (if specified)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        loguru_logger.add(
            log_file,
            level=level,
            format=format_string,
            rotation=rotation,
            retention=retention,
            compression="zip",
            backtrace=True,
            diagnose=True
        )
    
    # Intercept standard logging
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    
    # Set levels for noisy libraries
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)
    logging.getLogger("tensorflow").setLevel(logging.WARNING)
    logging.getLogger("torch").setLevel(logging.WARNING)


def get_logger(name: str = __name__):
    """
    Get a logger instance
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    return loguru_logger.bind(name=name)


# Configure logger for the package
def configure_package_logger():
    """Configure logger for the edge AI package"""
    from .config import get_config
    
    config = get_config()
    
    log_file = None
    if not config.debug:
        log_file = "logs/edge_ai.log"
    
    setup_logger(
        level=config.log_level,
        log_file=log_file,
        rotation="50 MB",
        retention="7 days"
    )


# Initialize logger when module is imported
configure_package_logger()

# Export the main logger
logger = get_logger(__name__)
