"""Data models for the AI Test Solver application."""

from .test import (
    TestStatus,
    QuestionType,
    TestCreate,
    TestResponse,
    TestUpdate,
    QuestionCreate,
    QuestionResponse,
    QuestionUpdate,
    ProcessingJobCreate,
    ProcessingJobResponse,
)

from .knowledge import (
    KnowledgeBaseEntry,
    KnowledgeSearchResult,
    EmbeddingRequest,
    EmbeddingResponse,
)

from .api import (
    BaseResponse,
    ErrorResponse,
    HealthResponse,
    UploadResponse,
    StatusResponse,
)

__all__ = [
    # Test models
    "TestStatus",
    "QuestionType", 
    "TestCreate",
    "TestResponse",
    "TestUpdate",
    "QuestionCreate",
    "QuestionResponse",
    "QuestionUpdate",
    "ProcessingJobCreate",
    "ProcessingJobResponse",
    
    # Knowledge models
    "KnowledgeBaseEntry",
    "KnowledgeSearchResult",
    "EmbeddingRequest",
    "EmbeddingResponse",
    
    # API models
    "BaseResponse",
    "ErrorResponse",
    "HealthResponse", 
    "UploadResponse",
    "StatusResponse",
]