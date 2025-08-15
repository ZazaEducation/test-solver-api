"""LLM service using OpenAI GPT-4o-mini for question solving."""

import asyncio
from typing import Dict, Any, Optional, Union
from functools import lru_cache

import openai
from asyncio_throttle import Throttler

from ..core import get_logger, settings, ExternalAPIError
from ..models.test import QuestionType

logger = get_logger(__name__)


class LLMService:
    """Service for interacting with OpenAI's LLM for question solving."""
    
    def __init__(self):
        """Initialize the LLM service."""
        self.client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
        # Rate limiting: OpenAI allows high throughput but we want to be responsible
        self.throttler = Throttler(rate_limit=50, period=60)  # 50 requests per minute
    
    async def generate_response(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.1,
        response_format: str = "text"
    ) -> str:
        """
        Generate a response using OpenAI's LLM.
        
        Args:
            prompt: Input prompt for the LLM
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0.0-1.0)
            response_format: Format of response ("text" or "json")
            
        Returns:
            Generated response text
            
        Raises:
            ExternalAPIError: If API call fails
        """
        async with self.throttler:
            try:
                logger.info(
                    "Generating LLM response",
                    model=settings.openai_model,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
                
                messages = [{"role": "user", "content": prompt}]
                
                # Prepare request parameters
                request_params = {
                    "model": settings.openai_model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                }
                
                # Add response format if JSON requested
                if response_format == "json":
                    request_params["response_format"] = {"type": "json_object"}
                
                response = await self.client.chat.completions.create(**request_params)
                
                if not response.choices:
                    raise ExternalAPIError("No response choices returned from OpenAI")
                
                content = response.choices[0].message.content
                if not content:
                    raise ExternalAPIError("Empty response content from OpenAI")
                
                logger.info(
                    "LLM response generated successfully",
                    response_length=len(content),
                    tokens_used=response.usage.total_tokens if response.usage else None
                )
                
                return content
                
            except openai.APIError as exc:
                logger.error(
                    "OpenAI API error",
                    error=str(exc),
                    error_code=getattr(exc, 'code', None)
                )
                raise ExternalAPIError(
                    f"OpenAI API error: {str(exc)}",
                    api_name="openai",
                    status_code=getattr(exc, 'status_code', None)
                ) from exc
            except Exception as exc:
                logger.error("LLM response generation failed", error=str(exc), exc_info=True)
                raise ExternalAPIError(f"LLM service error: {str(exc)}") from exc
    
    async def solve_question(
        self,
        question_text: str,
        question_type: QuestionType,
        options: list = None,
        context: str = None
    ) -> Dict[str, Any]:
        """
        Solve a single question using the LLM with RAG context.
        
        Args:
            question_text: The question to solve
            question_type: Type of question
            options: List of options for multiple choice questions
            context: Additional context from RAG system
            
        Returns:
            Dictionary with answer, confidence, and explanation
        """
        try:
            # Build context-aware prompt
            prompt = self._build_question_prompt(
                question_text, question_type, options, context
            )
            
            # Generate response
            response = await self.generate_response(
                prompt=prompt,
                max_tokens=800,
                temperature=0.1,
                response_format="json"
            )
            
            # Parse and validate response
            import json
            result = json.loads(response)
            
            # Ensure required fields exist
            answer = result.get('answer', '')
            confidence = float(result.get('confidence', 0.5))
            explanation = result.get('explanation', '')
            
            # Validate confidence range
            confidence = max(0.0, min(1.0, confidence))
            
            logger.info(
                "Question solved successfully",
                question_type=question_type.value,
                confidence=confidence,
                answer_length=len(answer)
            )
            
            return {
                'answer': answer,
                'confidence': confidence,
                'explanation': explanation
            }
            
        except json.JSONDecodeError as exc:
            logger.error(
                "Failed to parse LLM JSON response",
                question_text=question_text[:100],
                response=response[:500] if 'response' in locals() else None,
                error=str(exc)
            )
            # Return fallback response
            return {
                'answer': 'Unable to process question due to parsing error',
                'confidence': 0.1,
                'explanation': 'The AI encountered an error while processing this question.'
            }
        except Exception as exc:
            logger.error(
                "Question solving failed",
                question_text=question_text[:100],
                error=str(exc),
                exc_info=True
            )
            # Return fallback response
            return {
                'answer': 'Unable to answer due to processing error',
                'confidence': 0.1,
                'explanation': f'An error occurred while processing this question: {str(exc)}'
            }
    
    def _build_question_prompt(
        self,
        question_text: str,
        question_type: QuestionType,
        options: list = None,
        context: str = None
    ) -> str:
        """
        Build a comprehensive prompt for question solving.
        
        Args:
            question_text: The question to solve
            question_type: Type of question
            options: List of options for multiple choice
            context: RAG context information
            
        Returns:
            Formatted prompt string
        """
        # Base prompt with role definition
        prompt_parts = [
            "You are an expert AI assistant that answers test questions across all subjects.",
            "You have access to a broad knowledge base and use step-by-step reasoning.",
            ""
        ]
        
        # Add context if available
        if context and context.strip():
            prompt_parts.extend([
                "RELEVANT CONTEXT:",
                context.strip(),
                ""
            ])
        
        # Add question type specific instructions
        type_instructions = {
            QuestionType.MULTIPLE_CHOICE: "Select the best answer from the given options. Provide the option text, not just the letter.",
            QuestionType.SHORT_ANSWER: "Provide a concise, accurate answer in 1-3 sentences.",
            QuestionType.ESSAY: "Provide a comprehensive answer with multiple paragraphs and detailed explanation.",
            QuestionType.TRUE_FALSE: "Answer 'True' or 'False' and explain your reasoning.",
            QuestionType.FILL_BLANK: "Provide the most appropriate word or phrase to fill the blank.",
            QuestionType.OTHER: "Answer the question using appropriate format based on what's being asked."
        }
        
        prompt_parts.extend([
            f"QUESTION TYPE: {question_type.value}",
            f"INSTRUCTION: {type_instructions[question_type]}",
            ""
        ])
        
        # Add the question
        prompt_parts.append(f"QUESTION: {question_text}")
        
        # Add options for multiple choice
        if question_type == QuestionType.MULTIPLE_CHOICE and options:
            prompt_parts.append("\nOPTIONS:")
            for i, option in enumerate(options, 1):
                prompt_parts.append(f"{chr(64+i)}) {option}")
            prompt_parts.append("")
        
        # Add response format requirements
        prompt_parts.extend([
            "",
            "Respond with a JSON object containing:",
            "{",
            '  "answer": "Your direct answer to the question",',
            '  "confidence": 0.85,  // Your confidence level from 0.0 to 1.0',
            '  "explanation": "Step-by-step reasoning for your answer"',
            "}",
            "",
            "Important:",
            "- Base your answer on factual knowledge and logical reasoning",
            "- If you're unsure, indicate lower confidence but still provide your best answer",
            "- Keep explanations clear and educational",
            "- For multiple choice, ensure your answer matches one of the provided options exactly"
        ])
        
        return "\n".join(prompt_parts)


@lru_cache()
def get_llm_service() -> LLMService:
    """Get singleton LLM service instance."""
    return LLMService()