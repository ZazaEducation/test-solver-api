"""Structured logging configuration."""

import logging
import sys
from typing import Any, Dict

import structlog
from structlog.types import Processor

from .config import settings


def setup_logging() -> None:
    """Configure structured logging for the application."""
    
    # Configure structlog
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="ISO"),
    ]
    
    if settings.is_development():
        # Pretty console output for development
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        # JSON output for production
        processors.append(structlog.processors.JSONRenderer())
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.log_level.upper(), logging.INFO)
        ),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        context_class=dict,
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
    )
    
    # Reduce noise from external libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("supabase").setLevel(logging.WARNING)


def get_logger(name: str, **initial_context: Any) -> structlog.BoundLogger:
    """Get a structured logger instance.
    
    Args:
        name: Logger name (typically __name__)
        **initial_context: Initial context to bind to the logger
    
    Returns:
        Configured logger instance
    """
    logger = structlog.get_logger(name)
    if initial_context:
        logger = logger.bind(**initial_context)
    return logger


def add_request_context(
    request_id: str,
    method: str,
    path: str,
    user_id: str = None,
    **kwargs: Any
) -> Dict[str, Any]:
    """Create request context for logging.
    
    Args:
        request_id: Unique request identifier
        method: HTTP method
        path: Request path
        user_id: Optional user identifier
        **kwargs: Additional context
    
    Returns:
        Context dictionary
    """
    context = {
        "request_id": request_id,
        "method": method,
        "path": path,
        **kwargs
    }
    
    if user_id:
        context["user_id"] = user_id
    
    return context


def add_processing_context(
    test_id: str,
    stage: str,
    **kwargs: Any
) -> Dict[str, Any]:
    """Create processing context for logging.
    
    Args:
        test_id: Test identifier
        stage: Processing stage name
        **kwargs: Additional context
    
    Returns:
        Context dictionary
    """
    return {
        "test_id": test_id,
        "processing_stage": stage,
        **kwargs
    }