"""Test processing endpoints."""

import asyncio
from typing import Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status, BackgroundTasks
from fastapi.responses import JSONResponse

from ..core import get_logger, settings
from ..models.api import UploadResponse, StatusResponse, ErrorResponse
from ..models.test import TestResponse, TestStatus
from ..services import (
    DatabaseService,
    FileStorageService,
    TestProcessingService,
    get_database_service,
    get_file_storage_service,
    get_test_processing_service,
)

router = APIRouter()
logger = get_logger(__name__)

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/png", 
    "image/jpeg",
    "image/tiff",
    "image/bmp",
}


async def validate_file(file: UploadFile) -> None:
    """Validate uploaded file."""
    # Check file size
    if file.size and file.size > settings.max_file_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size {file.size} exceeds maximum allowed size of {settings.max_file_size_mb}MB"
        )
    
    # Check file extension
    if file.filename:
        file_ext = "." + file.filename.split(".")[-1].lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"File type not supported. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
            )
    
    # Check MIME type
    if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"MIME type {file.content_type} not supported"
        )


@router.post("/tests/upload", response_model=UploadResponse, tags=["Tests"])
async def upload_test(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Test file (PDF or image)"),
    title: str = Form(..., description="Test title"),
    created_by: str = Form(..., description="Email of the user creating the test"),
    db: DatabaseService = Depends(get_database_service),
    storage: FileStorageService = Depends(get_file_storage_service),
    processor: TestProcessingService = Depends(get_test_processing_service),
):
    """
    Upload a test file for processing.
    
    Args:
        file: PDF or image file containing test questions
        title: Title/name for the test
        created_by: Email of the user creating the test
    
    Returns:
        Upload confirmation with test ID and processing status
    """
    logger.info(
        "Processing test upload",
        filename=file.filename,
        content_type=file.content_type,
        size=file.size,
        title=title,
        created_by=created_by,
    )
    
    # Validate the file
    await validate_file(file)
    
    try:
        # Upload file to storage
        file_url = await storage.upload_file(file)
        logger.info("File uploaded to storage", file_url=file_url)
        
        # Create test record in database
        test_data = {
            "title": title,
            "file_url": file_url,
            "original_filename": file.filename or "unknown",
            "created_by": created_by,
        }
        
        test = await db.create_test(test_data)
        logger.info("Test record created", test_id=str(test.id))
        
        # Start background processing
        background_tasks.add_task(
            processor.process_test_async,
            test_id=test.id,
            file_url=file_url,
        )
        
        logger.info(
            "Test processing started",
            test_id=str(test.id),
            estimated_time=settings.max_processing_time_seconds,
        )
        
        return UploadResponse(
            test_id=str(test.id),
            file_url=file_url,
            estimated_time=settings.max_processing_time_seconds,
        )
        
    except Exception as exc:
        logger.error(
            "Failed to upload test",
            error=str(exc),
            filename=file.filename,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload and process test file"
        ) from exc


@router.get("/tests/{test_id}", response_model=TestResponse, tags=["Tests"])
async def get_test(
    test_id: UUID,
    db: DatabaseService = Depends(get_database_service),
):
    """
    Get test results and current status.
    
    Args:
        test_id: UUID of the test to retrieve
    
    Returns:
        Complete test data including questions and answers (if processing is complete)
    """
    logger.info("Retrieving test", test_id=str(test_id))
    
    try:
        test = await db.get_test_with_questions(test_id)
        if not test:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Test {test_id} not found"
            )
        
        logger.info(
            "Test retrieved",
            test_id=str(test_id),
            status=test.status,
            total_questions=test.total_questions,
        )
        
        return test
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Failed to retrieve test",
            test_id=str(test_id),
            error=str(exc),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve test data"
        ) from exc


@router.get("/tests/{test_id}/status", response_model=StatusResponse, tags=["Tests"])
async def get_test_status(
    test_id: UUID,
    db: DatabaseService = Depends(get_database_service),
):
    """
    Get test processing status.
    
    Args:
        test_id: UUID of the test to check
    
    Returns:
        Current processing status and progress information
    """
    logger.info("Checking test status", test_id=str(test_id))
    
    try:
        test = await db.get_test(test_id)
        if not test:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Test {test_id} not found"
            )
        
        # Get processing progress
        progress = {}
        if test.status == TestStatus.PROCESSING:
            # Get processing jobs to show progress
            jobs = await db.get_processing_jobs(test_id)
            progress = {
                "total_jobs": len(jobs),
                "completed_jobs": len([j for j in jobs if j.status == "completed"]),
                "failed_jobs": len([j for j in jobs if j.status == "failed"]),
                "current_stage": "processing_questions" if jobs else "extracting_questions",
            }
        
        logger.info(
            "Test status retrieved",
            test_id=str(test_id),
            status=test.status,
            progress=progress,
        )
        
        return StatusResponse(
            test_id=str(test_id),
            status=test.status.value,
            progress=progress,
        )
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Failed to retrieve test status",
            test_id=str(test_id),
            error=str(exc),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve test status"
        ) from exc


@router.delete("/tests/{test_id}", tags=["Tests"])
async def delete_test(
    test_id: UUID,
    db: DatabaseService = Depends(get_database_service),
    storage: FileStorageService = Depends(get_file_storage_service),
):
    """
    Delete a test and all associated data.
    
    Args:
        test_id: UUID of the test to delete
    
    Returns:
        Confirmation of deletion
    """
    logger.info("Deleting test", test_id=str(test_id))
    
    try:
        test = await db.get_test(test_id)
        if not test:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Test {test_id} not found"
            )
        
        # Delete file from storage
        if test.file_url:
            await storage.delete_file(test.file_url)
        
        # Delete test from database (cascade will delete questions and jobs)
        await db.delete_test(test_id)
        
        logger.info("Test deleted successfully", test_id=str(test_id))
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "message": f"Test {test_id} deleted successfully"
            }
        )
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Failed to delete test",
            test_id=str(test_id),
            error=str(exc),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete test"
        ) from exc