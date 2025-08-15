"""Question extraction service using LLM to parse and structure questions."""

import asyncio
import re
from typing import List, Dict, Any, Optional
from functools import lru_cache

from ..core import get_logger, QuestionExtractionError
from ..models.test import QuestionType, QuestionCreate
from .llm import LLMService, get_llm_service

logger = get_logger(__name__)


class QuestionExtractionService:
    """Service for extracting and structuring questions from raw text."""
    
    def __init__(self, llm_service: Optional[LLMService] = None):
        """Initialize the question extraction service."""
        self.llm_service = llm_service or get_llm_service()
    
    async def extract_questions(self, text: str, test_id: str) -> List[QuestionCreate]:
        """
        Extract structured questions from raw OCR text.
        
        Args:
            text: Raw text extracted from OCR
            test_id: UUID of the test for linking questions
            
        Returns:
            List of structured question objects
            
        Raises:
            QuestionExtractionError: If question extraction fails
        """
        try:
            logger.info(
                "Starting question extraction",
                test_id=test_id,
                text_length=len(text)
            )
            
            # Pre-process text to clean up OCR artifacts
            cleaned_text = self._preprocess_text(text)
            
            # Use LLM to extract and structure questions
            structured_questions = await self._extract_with_llm(cleaned_text, test_id)
            
            # Post-process and validate questions
            validated_questions = self._validate_questions(structured_questions, test_id)
            
            logger.info(
                "Question extraction completed",
                test_id=test_id,
                questions_extracted=len(validated_questions)
            )
            
            return validated_questions
            
        except Exception as exc:
            logger.error(
                "Question extraction failed",
                test_id=test_id,
                error=str(exc),
                exc_info=True
            )
            raise QuestionExtractionError(f"Failed to extract questions: {str(exc)}") from exc
    
    def _preprocess_text(self, text: str) -> str:
        """
        Clean and preprocess OCR text for better question extraction.
        
        Args:
            text: Raw OCR text
            
        Returns:
            Cleaned text
        """
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Fix common OCR errors
        text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)  # Missing spaces before capitals
        text = re.sub(r'(\d+)\.([A-Za-z])', r'\1. \2', text)  # Missing spaces after question numbers
        text = re.sub(r'([a-z])\)([A-Za-z])', r'\1) \2', text)  # Missing spaces after options
        
        # Normalize question markers
        text = re.sub(r'Question\s*(\d+)', r'Question \1:', text, flags=re.IGNORECASE)
        text = re.sub(r'Q\s*(\d+)', r'Question \1:', text, flags=re.IGNORECASE)
        
        # Normalize option markers
        text = re.sub(r'\b([A-E])\)', r'\1)', text)
        text = re.sub(r'\b([a-e])\)', r'\1)', text)
        
        return text.strip()
    
    async def _extract_with_llm(self, text: str, test_id: str) -> List[Dict[str, Any]]:
        """
        Use LLM to extract structured questions from text.
        
        Args:
            text: Preprocessed text
            test_id: Test identifier
            
        Returns:
            List of question dictionaries
        """
        prompt = f"""
        Extract all questions from the following text and structure them as JSON. 
        
        For each question, identify:
        1. The question number (if available, otherwise assign sequentially)
        2. The complete question text
        3. The question type: multiple_choice, short_answer, essay, true_false, fill_blank, or other
        4. For multiple choice questions, extract all options (A, B, C, D, E, etc.)
        
        Return a JSON array where each question follows this structure:
        {{
            "question_number": 1,
            "question_text": "What is the capital of France?",
            "question_type": "multiple_choice",
            "options": ["Paris", "London", "Berlin", "Madrid"]
        }}
        
        Rules:
        - Keep the original question text exactly as written
        - For multiple choice, extract only the option text, not the letter markers (A), B), etc.)
        - If no clear question type can be determined, use "other"
        - Number questions sequentially starting from 1 if no numbers are present
        - Include all questions found, even if partial or unclear
        
        Text to process:
        {text}
        
        Return only the JSON array, no additional text.
        """
        
        try:
            response = await self.llm_service.generate_response(
                prompt=prompt,
                max_tokens=4000,
                temperature=0.1,
                response_format="json"
            )
            
            # Parse JSON response
            import json
            questions_data = json.loads(response)
            
            if not isinstance(questions_data, list):
                raise QuestionExtractionError("LLM response is not a valid JSON array")
            
            logger.info(
                "LLM question extraction completed",
                test_id=test_id,
                questions_found=len(questions_data)
            )
            
            return questions_data
            
        except json.JSONDecodeError as exc:
            logger.error(
                "Failed to parse LLM JSON response",
                test_id=test_id,
                response=response[:500],
                error=str(exc)
            )
            raise QuestionExtractionError(f"Invalid JSON response from LLM: {str(exc)}") from exc
        except Exception as exc:
            logger.error(
                "LLM question extraction failed",
                test_id=test_id,
                error=str(exc)
            )
            raise QuestionExtractionError(f"LLM extraction failed: {str(exc)}") from exc
    
    def _validate_questions(self, questions_data: List[Dict[str, Any]], test_id: str) -> List[QuestionCreate]:
        """
        Validate and convert question dictionaries to QuestionCreate objects.
        
        Args:
            questions_data: Raw question dictionaries from LLM
            test_id: Test identifier
            
        Returns:
            List of validated QuestionCreate objects
        """
        validated_questions = []
        
        for i, question_data in enumerate(questions_data):
            try:
                # Ensure required fields exist
                question_number = question_data.get('question_number', i + 1)
                question_text = question_data.get('question_text', '').strip()
                
                if not question_text:
                    logger.warning(f"Skipping question {question_number}: empty text")
                    continue
                
                # Validate and normalize question type
                question_type_str = question_data.get('question_type', 'other').lower()
                question_type = self._normalize_question_type(question_type_str)
                
                # Handle options
                options = question_data.get('options', [])
                if isinstance(options, str):
                    options = [opt.strip() for opt in options.split('\n') if opt.strip()]
                elif not isinstance(options, list):
                    options = []
                
                # Ensure multiple choice questions have options
                if question_type == QuestionType.MULTIPLE_CHOICE and not options:
                    logger.warning(
                        f"Multiple choice question {question_number} has no options, "
                        "changing type to 'other'"
                    )
                    question_type = QuestionType.OTHER
                
                # Create validated question
                question = QuestionCreate(
                    test_id=test_id,
                    question_number=question_number,
                    question_text=question_text,
                    question_type=question_type,
                    options=options
                )
                
                validated_questions.append(question)
                
            except Exception as exc:
                logger.warning(
                    f"Failed to validate question {i + 1}",
                    error=str(exc),
                    question_data=question_data
                )
                continue
        
        if not validated_questions:
            raise QuestionExtractionError("No valid questions could be extracted from the text")
        
        logger.info(
            "Question validation completed",
            test_id=test_id,
            total_questions=len(validated_questions)
        )
        
        return validated_questions
    
    def _normalize_question_type(self, type_str: str) -> QuestionType:
        """
        Normalize question type string to QuestionType enum.
        
        Args:
            type_str: String representation of question type
            
        Returns:
            Normalized QuestionType enum value
        """
        type_str = type_str.lower().replace(' ', '_').replace('-', '_')
        
        type_mapping = {
            'multiple_choice': QuestionType.MULTIPLE_CHOICE,
            'multichoice': QuestionType.MULTIPLE_CHOICE,
            'mc': QuestionType.MULTIPLE_CHOICE,
            'short_answer': QuestionType.SHORT_ANSWER,
            'short': QuestionType.SHORT_ANSWER,
            'essay': QuestionType.ESSAY,
            'long_answer': QuestionType.ESSAY,
            'true_false': QuestionType.TRUE_FALSE,
            'boolean': QuestionType.TRUE_FALSE,
            'tf': QuestionType.TRUE_FALSE,
            'fill_blank': QuestionType.FILL_BLANK,
            'fill_in': QuestionType.FILL_BLANK,
            'fill_in_the_blank': QuestionType.FILL_BLANK,
            'blank': QuestionType.FILL_BLANK,
        }
        
        return type_mapping.get(type_str, QuestionType.OTHER)


@lru_cache()
def get_question_extraction_service() -> QuestionExtractionService:
    """Get singleton question extraction service instance."""
    return QuestionExtractionService()