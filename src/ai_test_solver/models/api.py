"""API response models."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class BaseResponse(BaseModel):
    """Base response model."""
    success: bool = Field(default=True, description="Whether the request was successful")
    message: Optional[str] = Field(None, description="Response message")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class ErrorResponse(BaseResponse):
    """Error response model."""
    success: bool = Field(default=False, description="Always false for errors")
    error_code: Optional[str] = Field(None, description="Machine-readable error code")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    
    def __init__(self, message: str, error_code: str = None, details: Dict[str, Any] = None, **kwargs):
        super().__init__(
            success=False,
            message=message,
            error_code=error_code,
            details=details or {},
            **kwargs
        )


class HealthResponse(BaseResponse):
    """Health check response model."""
    status: str = Field(..., description="Application status")
    version: str = Field(..., description="Application version")
    environment: str = Field(..., description="Environment name")
    database_connected: bool = Field(..., description="Database connection status")
    external_services: Dict[str, bool] = Field(
        default_factory=dict,
        description="Status of external service connections"
    )


class UploadResponse(BaseResponse):
    """File upload response model."""
    test_id: str = Field(..., description="Generated test ID")
    file_url: str = Field(..., description="URL of the uploaded file")
    estimated_processing_time: int = Field(
        ..., description="Estimated processing time in seconds"
    )
    
    def __init__(self, test_id: str, file_url: str, estimated_time: int = 300, **kwargs):
        super().__init__(
            test_id=test_id,
            file_url=file_url,
            estimated_processing_time=estimated_time,
            message="File uploaded successfully. Processing started.",
            **kwargs
        )


class StatusResponse(BaseResponse):
    """Test status response model."""
    test_id: str = Field(..., description="Test ID")
    status: str = Field(..., description="Current processing status")
    progress: Optional[Dict[str, Any]] = Field(None, description="Processing progress information")
    estimated_completion: Optional[datetime] = Field(
        None, description="Estimated completion time"
    )
    
    def __init__(
        self,
        test_id: str,
        status: str,
        progress: Dict[str, Any] = None,
        estimated_completion: datetime = None,
        **kwargs
    ):
        message = f"Test {test_id} is {status}"
        if status == "completed":
            message += ". Results are available."
        elif status == "failed":
            message += ". Processing failed."
        else:
            message += ". Processing in progress."
            
        super().__init__(
            test_id=test_id,
            status=status,
            progress=progress or {},
            estimated_completion=estimated_completion,
            message=message,
            **kwargs
        )


class ValidationErrorDetail(BaseModel):
    """Model for validation error details."""
    field: str = Field(..., description="Field name that failed validation")
    message: str = Field(..., description="Validation error message")
    value: Any = Field(None, description="Invalid value")


class ValidationErrorResponse(ErrorResponse):
    """Validation error response model."""
    validation_errors: List[ValidationErrorDetail] = Field(
        default_factory=list,
        description="List of validation errors"
    )
    
    def __init__(self, validation_errors: List[ValidationErrorDetail], **kwargs):
        super().__init__(
            message="Validation failed",
            error_code="VALIDATION_ERROR",
            details={"validation_errors": [error.dict() for error in validation_errors]},
            validation_errors=validation_errors,
            **kwargs
        )


class PaginatedResponse(BaseResponse):
    """Base paginated response model."""
    page: int = Field(..., ge=1, description="Current page number")
    per_page: int = Field(..., ge=1, le=100, description="Items per page")
    total: int = Field(..., ge=0, description="Total number of items")
    total_pages: int = Field(..., ge=1, description="Total number of pages")
    has_next: bool = Field(..., description="Whether there's a next page")
    has_prev: bool = Field(..., description="Whether there's a previous page")