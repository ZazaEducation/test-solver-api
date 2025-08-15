"""Database service for interacting with Supabase PostgreSQL."""

import asyncio
from typing import List, Optional, Dict, Any
from uuid import UUID
from functools import lru_cache

import asyncpg
from supabase import create_client, Client

from ..core import get_logger, settings, DatabaseError
from ..models.test import (
    TestCreate, TestResponse, TestUpdate, TestStatus,
    QuestionCreate, QuestionResponse, QuestionUpdate,
    ProcessingJobCreate, ProcessingJobResponse
)

logger = get_logger(__name__)


class DatabaseService:
    """Service for database operations using Supabase/PostgreSQL."""
    
    def __init__(self):
        """Initialize the database service."""
        self._supabase_client: Optional[Client] = None
        self._db_pool: Optional[asyncpg.Pool] = None
    
    async def connect(self) -> None:
        """Initialize database connections."""
        try:
            # Initialize Supabase client for auth and admin operations
            self._supabase_client = create_client(
                settings.supabase_url,
                settings.supabase_service_key
            )
            
            # Create direct PostgreSQL connection pool for performance
            if settings.database_url:
                self._db_pool = await asyncpg.create_pool(
                    settings.database_url,
                    min_size=2,
                    max_size=10,
                    command_timeout=60
                )
                logger.info("Database connection pool created")
            
            logger.info("Database service initialized")
            
        except Exception as exc:
            logger.error("Failed to initialize database service", error=str(exc))
            raise DatabaseError(f"Database initialization failed: {str(exc)}") from exc
    
    async def disconnect(self) -> None:
        """Close database connections."""
        if self._db_pool:
            await self._db_pool.close()
            logger.info("Database connection pool closed")
    
    async def health_check(self) -> bool:
        """Check database connectivity."""
        try:
            if self._db_pool:
                async with self._db_pool.acquire() as conn:
                    await conn.fetchval("SELECT 1")
                return True
            return False
        except Exception as exc:
            logger.error("Database health check failed", error=str(exc))
            return False
    
    # Test operations
    async def create_test(self, test_data: Dict[str, Any]) -> TestResponse:
        """Create a new test record."""
        try:
            query = """
                INSERT INTO tests (title, file_url, original_filename, created_by)
                VALUES ($1, $2, $3, $4)
                RETURNING id, created_date, updated_date, title, file_url, 
                         original_filename, created_by, status, processing_time, total_questions
            """
            
            async with self._db_pool.acquire() as conn:
                record = await conn.fetchrow(
                    query,
                    test_data['title'],
                    test_data['file_url'], 
                    test_data['original_filename'],
                    test_data['created_by']
                )
            
            logger.info("Test created", test_id=str(record['id']))
            
            return TestResponse(
                id=str(record['id']),
                created_date=record['created_date'],
                updated_date=record['updated_date'],
                created_by=record['created_by'],
                title=record['title'],
                file_url=record['file_url'],
                original_filename=record['original_filename'],
                status=TestStatus(record['status']),
                questions=[],
                processing_time=record['processing_time'],
                total_questions=record['total_questions'] or 0
            )
            
        except Exception as exc:
            logger.error("Failed to create test", error=str(exc), test_data=test_data)
            raise DatabaseError(f"Failed to create test: {str(exc)}") from exc
    
    async def get_test(self, test_id: UUID) -> Optional[TestResponse]:
        """Get a test by ID."""
        try:
            query = """
                SELECT id, created_date, updated_date, created_by, title, file_url,
                       original_filename, status, processing_time, total_questions
                FROM tests WHERE id = $1
            """
            
            async with self._db_pool.acquire() as conn:
                record = await conn.fetchrow(query, test_id)
            
            if not record:
                return None
            
            return TestResponse(
                id=str(record['id']),
                created_date=record['created_date'],
                updated_date=record['updated_date'],
                created_by=record['created_by'],
                title=record['title'],
                file_url=record['file_url'],
                original_filename=record['original_filename'],
                status=TestStatus(record['status']),
                questions=[],
                processing_time=record['processing_time'],
                total_questions=record['total_questions'] or 0
            )
            
        except Exception as exc:
            logger.error("Failed to get test", test_id=str(test_id), error=str(exc))
            raise DatabaseError(f"Failed to get test: {str(exc)}") from exc
    
    async def get_test_with_questions(self, test_id: UUID) -> Optional[TestResponse]:
        """Get a test with all its questions."""
        try:
            # Get test data
            test = await self.get_test(test_id)
            if not test:
                return None
            
            # Get questions
            questions = await self.get_test_questions(test_id)
            test.questions = questions
            
            return test
            
        except Exception as exc:
            logger.error("Failed to get test with questions", test_id=str(test_id), error=str(exc))
            raise DatabaseError(f"Failed to get test with questions: {str(exc)}") from exc
    
    async def update_test(self, test_id: UUID, updates: Dict[str, Any]) -> bool:
        """Update a test record."""
        try:
            # Build dynamic update query
            set_clauses = []
            values = []
            param_num = 1
            
            for field, value in updates.items():
                set_clauses.append(f"{field} = ${param_num}")
                values.append(value)
                param_num += 1
            
            if not set_clauses:
                return True  # Nothing to update
            
            query = f"""
                UPDATE tests 
                SET {', '.join(set_clauses)}, updated_date = NOW()
                WHERE id = ${param_num}
            """
            values.append(test_id)
            
            async with self._db_pool.acquire() as conn:
                result = await conn.execute(query, *values)
            
            success = result == "UPDATE 1"
            if success:
                logger.info("Test updated", test_id=str(test_id), updates=list(updates.keys()))
            
            return success
            
        except Exception as exc:
            logger.error("Failed to update test", test_id=str(test_id), error=str(exc))
            raise DatabaseError(f"Failed to update test: {str(exc)}") from exc
    
    async def delete_test(self, test_id: UUID) -> bool:
        """Delete a test and all associated data."""
        try:
            query = "DELETE FROM tests WHERE id = $1"
            
            async with self._db_pool.acquire() as conn:
                result = await conn.execute(query, test_id)
            
            success = result == "DELETE 1"
            if success:
                logger.info("Test deleted", test_id=str(test_id))
            
            return success
            
        except Exception as exc:
            logger.error("Failed to delete test", test_id=str(test_id), error=str(exc))
            raise DatabaseError(f"Failed to delete test: {str(exc)}") from exc
    
    # Question operations
    async def create_questions(self, questions: List[QuestionCreate]) -> List[QuestionResponse]:
        """Create multiple questions."""
        if not questions:
            return []
        
        try:
            query = """
                INSERT INTO questions (test_id, question_number, question_text, question_type, options)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id, test_id, question_number, question_text, question_type, options,
                         ai_answer, confidence, explanation
            """
            
            results = []
            async with self._db_pool.acquire() as conn:
                for question in questions:
                    record = await conn.fetchrow(
                        query,
                        question.test_id,
                        question.question_number,
                        question.question_text,
                        question.question_type.value,
                        question.options
                    )
                    
                    results.append(QuestionResponse(
                        question_number=record['question_number'],
                        question_text=record['question_text'],
                        question_type=record['question_type'],
                        options=record['options'] or [],
                        ai_answer=record['ai_answer'],
                        confidence=float(record['confidence']) if record['confidence'] else None,
                        explanation=record['explanation']
                    ))
            
            logger.info("Questions created", count=len(results))
            return results
            
        except Exception as exc:
            logger.error("Failed to create questions", error=str(exc))
            raise DatabaseError(f"Failed to create questions: {str(exc)}") from exc
    
    async def get_test_questions(self, test_id: UUID) -> List[QuestionResponse]:
        """Get all questions for a test."""
        try:
            query = """
                SELECT question_number, question_text, question_type, options,
                       ai_answer, confidence, explanation
                FROM questions 
                WHERE test_id = $1 
                ORDER BY question_number
            """
            
            async with self._db_pool.acquire() as conn:
                records = await conn.fetch(query, test_id)
            
            questions = []
            for record in records:
                questions.append(QuestionResponse(
                    question_number=record['question_number'],
                    question_text=record['question_text'],
                    question_type=record['question_type'],
                    options=record['options'] or [],
                    ai_answer=record['ai_answer'],
                    confidence=float(record['confidence']) if record['confidence'] else None,
                    explanation=record['explanation']
                ))
            
            return questions
            
        except Exception as exc:
            logger.error("Failed to get test questions", test_id=str(test_id), error=str(exc))
            raise DatabaseError(f"Failed to get test questions: {str(exc)}") from exc
    
    async def update_question_answer(
        self, 
        test_id: UUID, 
        question_number: int, 
        answer_data: Dict[str, Any]
    ) -> bool:
        """Update a question with AI-generated answer."""
        try:
            query = """
                UPDATE questions 
                SET ai_answer = $1, confidence = $2, explanation = $3, processing_time = $4,
                    updated_date = NOW()
                WHERE test_id = $5 AND question_number = $6
            """
            
            async with self._db_pool.acquire() as conn:
                result = await conn.execute(
                    query,
                    answer_data.get('answer'),
                    answer_data.get('confidence'),
                    answer_data.get('explanation'),
                    answer_data.get('processing_time'),
                    test_id,
                    question_number
                )
            
            success = result == "UPDATE 1"
            if success:
                logger.info(
                    "Question answer updated",
                    test_id=str(test_id),
                    question_number=question_number
                )
            
            return success
            
        except Exception as exc:
            logger.error(
                "Failed to update question answer",
                test_id=str(test_id),
                question_number=question_number,
                error=str(exc)
            )
            raise DatabaseError(f"Failed to update question answer: {str(exc)}") from exc
    
    # Processing job operations
    async def create_processing_job(self, job_data: ProcessingJobCreate) -> ProcessingJobResponse:
        """Create a processing job record."""
        try:
            query = """
                INSERT INTO processing_jobs (test_id, job_type, metadata)
                VALUES ($1, $2, $3)
                RETURNING id, test_id, job_type, status, started_at, completed_at, 
                         error_message, metadata, created_date
            """
            
            async with self._db_pool.acquire() as conn:
                record = await conn.fetchrow(
                    query,
                    job_data.test_id,
                    job_data.job_type,
                    job_data.metadata
                )
            
            return ProcessingJobResponse(**dict(record))
            
        except Exception as exc:
            logger.error("Failed to create processing job", error=str(exc))
            raise DatabaseError(f"Failed to create processing job: {str(exc)}") from exc
    
    async def get_processing_jobs(self, test_id: UUID) -> List[ProcessingJobResponse]:
        """Get all processing jobs for a test."""
        try:
            query = """
                SELECT id, test_id, job_type, status, started_at, completed_at,
                       error_message, metadata, created_date
                FROM processing_jobs
                WHERE test_id = $1
                ORDER BY created_date
            """
            
            async with self._db_pool.acquire() as conn:
                records = await conn.fetch(query, test_id)
            
            return [ProcessingJobResponse(**dict(record)) for record in records]
            
        except Exception as exc:
            logger.error("Failed to get processing jobs", test_id=str(test_id), error=str(exc))
            raise DatabaseError(f"Failed to get processing jobs: {str(exc)}") from exc


@lru_cache()
def get_database_service() -> DatabaseService:
    """Get singleton database service instance."""
    return DatabaseService()