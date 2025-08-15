"""Custom exception classes for the AI Test Solver application."""

from typing import Any, Dict, Optional


class TestSolverException(Exception):
    """Base exception class for all AI Test Solver errors."""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize the exception.
        
        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            details: Additional error details
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}


class ValidationError(TestSolverException):
    """Raised when input validation fails."""

    def __init__(self, message: str, field: Optional[str] = None, **kwargs) -> None:
        super().__init__(message, error_code="VALIDATION_ERROR", **kwargs)
        if field:
            self.details["field"] = field


class ProcessingError(TestSolverException):
    """Raised when test processing fails."""

    def __init__(self, message: str, stage: Optional[str] = None, **kwargs) -> None:
        super().__init__(message, error_code="PROCESSING_ERROR", **kwargs)
        if stage:
            self.details["stage"] = stage


class OCRError(TestSolverException):
    """Raised when OCR processing fails."""

    def __init__(self, message: str, **kwargs) -> None:
        super().__init__(message, error_code="OCR_ERROR", **kwargs)


class QuestionExtractionError(TestSolverException):
    """Raised when question extraction fails."""

    def __init__(self, message: str, **kwargs) -> None:
        super().__init__(message, error_code="QUESTION_EXTRACTION_ERROR", **kwargs)


class RAGError(TestSolverException):
    """Raised when RAG (Retrieval-Augmented Generation) processing fails."""

    def __init__(self, message: str, **kwargs) -> None:
        super().__init__(message, error_code="RAG_ERROR", **kwargs)


class ExternalAPIError(TestSolverException):
    """Raised when external API calls fail."""

    def __init__(
        self,
        message: str,
        api_name: Optional[str] = None,
        status_code: Optional[int] = None,
        **kwargs
    ) -> None:
        super().__init__(message, error_code="EXTERNAL_API_ERROR", **kwargs)
        if api_name:
            self.details["api_name"] = api_name
        if status_code:
            self.details["status_code"] = status_code


class DatabaseError(TestSolverException):
    """Raised when database operations fail."""

    def __init__(self, message: str, **kwargs) -> None:
        super().__init__(message, error_code="DATABASE_ERROR", **kwargs)


class FileProcessingError(TestSolverException):
    """Raised when file processing fails."""

    def __init__(
        self,
        message: str,
        filename: Optional[str] = None,
        file_type: Optional[str] = None,
        **kwargs
    ) -> None:
        super().__init__(message, error_code="FILE_PROCESSING_ERROR", **kwargs)
        if filename:
            self.details["filename"] = filename
        if file_type:
            self.details["file_type"] = file_type


class QuestionSolvingError(TestSolverException):
    """Raised when question solving fails."""

    def __init__(
        self,
        message: str,
        question_number: Optional[int] = None,
        question_type: Optional[str] = None,
        **kwargs
    ) -> None:
        super().__init__(message, error_code="QUESTION_SOLVING_ERROR", **kwargs)
        if question_number:
            self.details["question_number"] = question_number
        if question_type:
            self.details["question_type"] = question_type


class RateLimitError(TestSolverException):
    """Raised when rate limits are exceeded."""

    def __init__(self, message: str, retry_after: Optional[int] = None, **kwargs) -> None:
        super().__init__(message, error_code="RATE_LIMIT_ERROR", **kwargs)
        if retry_after:
            self.details["retry_after"] = retry_after


class AuthenticationError(TestSolverException):
    """Raised when authentication fails."""

    def __init__(self, message: str, **kwargs) -> None:
        super().__init__(message, error_code="AUTHENTICATION_ERROR", **kwargs)


class AuthorizationError(TestSolverException):
    """Raised when authorization fails."""

    def __init__(self, message: str, **kwargs) -> None:
        super().__init__(message, error_code="AUTHORIZATION_ERROR", **kwargs)