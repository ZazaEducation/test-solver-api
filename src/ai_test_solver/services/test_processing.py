"""Main test processing orchestrator that coordinates all services."""

import asyncio
import time
from typing import List, Optional, Dict, Any
from uuid import UUID
from functools import lru_cache

from ..core import get_logger, settings, ProcessingError
from ..models.test import TestStatus, QuestionCreate
from .database import DatabaseService, get_database_service
from .file_storage import FileStorageService, get_file_storage_service
from .ocr import OCRService, get_ocr_service
from .question_extraction import QuestionExtractionService, get_question_extraction_service
from .llm import LLMService, get_llm_service
from .rag import RAGService, get_rag_service

logger = get_logger(__name__)


class TestProcessingService:
    """Main orchestrator for test processing pipeline."""
    
    def __init__(
        self,
        db_service: Optional[DatabaseService] = None,
        storage_service: Optional[FileStorageService] = None,
        ocr_service: Optional[OCRService] = None,
        extraction_service: Optional[QuestionExtractionService] = None,
        llm_service: Optional[LLMService] = None,
        rag_service: Optional[RAGService] = None,
    ):
        """Initialize the test processing service."""
        self.db = db_service or get_database_service()
        self.storage = storage_service or get_file_storage_service()
        self.ocr = ocr_service or get_ocr_service()
        self.extractor = extraction_service or get_question_extraction_service()
        self.llm = llm_service or get_llm_service()
        self.rag = rag_service or get_rag_service()
    
    async def process_test_async(self, test_id: UUID, file_url: str) -> None:
        """
        Process a test file asynchronously.
        
        This is the main orchestration method that:
        1. Downloads and processes the file with OCR
        2. Extracts questions using LLM
        3. Solves questions concurrently using RAG + LLM
        4. Updates the database with results
        
        Args:
            test_id: UUID of the test to process
            file_url: URL of the uploaded test file
        """
        start_time = time.time()
        processing_context = {
            "test_id": str(test_id),
            "file_url": file_url,
            "stage": "initialization"
        }
        
        logger.info("Starting test processing", **processing_context)
        
        try:
            # Stage 1: Download and OCR the file
            processing_context["stage"] = "ocr"
            logger.info("Starting OCR processing", **processing_context)
            
            file_content = await self.storage.download_file(file_url)
            filename = file_url.split('/')[-1]
            extracted_text = await self.ocr.extract_text_from_file(file_content, filename)
            
            logger.info(
                "OCR completed",
                text_length=len(extracted_text),
                **processing_context
            )
            
            if not extracted_text.strip():
                raise ProcessingError("No text could be extracted from the file", stage="ocr")
            
            # Stage 2: Extract questions
            processing_context["stage"] = "question_extraction"
            logger.info("Starting question extraction", **processing_context)
            
            questions = await self.extractor.extract_questions(extracted_text, str(test_id))
            
            if not questions:
                raise ProcessingError("No questions could be extracted from the text", stage="question_extraction")
            
            logger.info(
                "Questions extracted",
                question_count=len(questions),
                **processing_context
            )
            
            # Create question records in database
            created_questions = await self.db.create_questions(questions)
            
            # Update test with question count
            await self.db.update_test(test_id, {"total_questions": len(questions)})
            
            # Stage 3: Solve questions concurrently
            processing_context["stage"] = "question_solving"
            logger.info("Starting concurrent question solving", **processing_context)
            
            # Process questions in batches to respect concurrency limits
            batch_size = settings.max_concurrent_questions
            question_batches = [
                questions[i:i + batch_size] 
                for i in range(0, len(questions), batch_size)
            ]
            
            total_solved = 0
            for batch_num, batch in enumerate(question_batches, 1):
                logger.info(
                    f"Processing batch {batch_num}/{len(question_batches)}",
                    batch_size=len(batch),
                    **processing_context
                )
                
                # Create concurrent tasks for this batch
                tasks = [
                    self._solve_question_with_rag(test_id, question)
                    for question in batch
                ]
                
                # Execute batch concurrently
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results
                for question, result in zip(batch, batch_results):
                    if isinstance(result, Exception):
                        logger.error(
                            "Question solving failed",
                            question_number=question.question_number,
                            error=str(result),
                            **processing_context
                        )
                        # Still update with error info
                        await self.db.update_question_answer(
                            test_id,
                            question.question_number,
                            {
                                "answer": "Error occurred during processing",
                                "confidence": 0.0,
                                "explanation": f"Processing error: {str(result)}"
                            }
                        )
                    else:
                        total_solved += 1
                
                # Small delay between batches to be respectful to APIs
                if batch_num < len(question_batches):
                    await asyncio.sleep(1)
            
            # Stage 4: Finalize processing
            processing_context["stage"] = "finalization"
            processing_time = time.time() - start_time
            
            logger.info(
                "Test processing completed successfully",
                total_questions=len(questions),
                questions_solved=total_solved,
                processing_time=processing_time,
                **processing_context
            )
            
            # Update test status to completed
            await self.db.update_test(
                test_id,
                {
                    "status": TestStatus.COMPLETED,
                    "processing_time": processing_time
                }
            )
            
        except Exception as exc:
            processing_time = time.time() - start_time
            error_message = f"Processing failed at stage '{processing_context['stage']}': {str(exc)}"
            
            logger.error(
                "Test processing failed",
                error=error_message,
                processing_time=processing_time,
                exc_info=True,
                **processing_context
            )
            
            # Update test status to failed
            await self.db.update_test(
                test_id,
                {
                    "status": TestStatus.FAILED,
                    "processing_time": processing_time,
                    "error_message": error_message
                }
            )
            
            raise ProcessingError(error_message, stage=processing_context["stage"]) from exc
    
    async def _solve_question_with_rag(self, test_id: UUID, question: QuestionCreate) -> Dict[str, Any]:
        """
        Solve a single question using RAG + LLM.
        
        Args:
            test_id: UUID of the test
            question: Question to solve
            
        Returns:
            Dictionary with solution data
            
        Raises:
            Exception: If question solving fails
        """
        question_start_time = time.time()
        
        try:
            logger.info(
                "Solving question",
                test_id=str(test_id),
                question_number=question.question_number,
                question_type=question.question_type.value
            )
            
            # Get relevant context using RAG
            rag_context = await self.rag.get_context_for_question(
                question.question_text,
                question_type=question.question_type.value
            )
            
            # Solve question using LLM with RAG context
            solution = await self.llm.solve_question(
                question_text=question.question_text,
                question_type=question.question_type,
                options=question.options,
                context=rag_context
            )
            
            # Add processing time
            processing_time = time.time() - question_start_time
            solution["processing_time"] = processing_time
            
            # Update database with solution
            await self.db.update_question_answer(
                test_id,
                question.question_number,
                solution
            )
            
            logger.info(
                "Question solved successfully",
                test_id=str(test_id),
                question_number=question.question_number,
                confidence=solution.get("confidence", 0.0),
                processing_time=processing_time
            )
            
            return solution
            
        except Exception as exc:
            processing_time = time.time() - question_start_time
            
            logger.error(
                "Question solving failed",
                test_id=str(test_id),
                question_number=question.question_number,
                error=str(exc),
                processing_time=processing_time,
                exc_info=True
            )
            
            # Re-raise the exception to be handled by the batch processor
            raise exc
    
    async def get_processing_status(self, test_id: UUID) -> Dict[str, Any]:
        """
        Get detailed processing status for a test.
        
        Args:
            test_id: UUID of the test
            
        Returns:
            Dictionary with detailed status information
        """
        try:
            test = await self.db.get_test(test_id)
            if not test:
                raise ProcessingError(f"Test {test_id} not found")
            
            status_info = {
                "test_id": str(test_id),
                "status": test.status.value,
                "total_questions": test.total_questions,
                "processing_time": test.processing_time,
            }
            
            # If processing is in progress, get more details
            if test.status == TestStatus.PROCESSING:
                questions = await self.db.get_test_questions(test_id)
                
                answered_questions = len([q for q in questions if q.ai_answer])
                
                status_info.update({
                    "questions_processed": answered_questions,
                    "questions_remaining": test.total_questions - answered_questions,
                    "progress_percentage": (answered_questions / test.total_questions * 100) if test.total_questions > 0 else 0
                })
            
            return status_info
            
        except Exception as exc:
            logger.error(
                "Failed to get processing status",
                test_id=str(test_id),
                error=str(exc)
            )
            raise ProcessingError(f"Failed to get processing status: {str(exc)}") from exc
    
    async def cancel_processing(self, test_id: UUID) -> bool:
        """
        Cancel processing for a test (if possible).
        
        Args:
            test_id: UUID of the test to cancel
            
        Returns:
            True if cancellation was successful
        """
        try:
            # For now, just update the status
            # In a more advanced implementation, you might need to track and cancel
            # running async tasks
            
            success = await self.db.update_test(
                test_id,
                {
                    "status": TestStatus.FAILED,
                    "error_message": "Processing cancelled by user"
                }
            )
            
            logger.info(
                "Test processing cancelled",
                test_id=str(test_id),
                success=success
            )
            
            return success
            
        except Exception as exc:
            logger.error(
                "Failed to cancel processing",
                test_id=str(test_id),
                error=str(exc)
            )
            return False


@lru_cache()
def get_test_processing_service() -> TestProcessingService:
    """Get singleton test processing service instance."""
    return TestProcessingService()