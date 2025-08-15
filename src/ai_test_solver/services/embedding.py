"""Embedding service using Sentence Transformers."""

import asyncio
from typing import List, Optional
from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer

from ..core import get_logger, ExternalAPIError

logger = get_logger(__name__)


class EmbeddingService:
    """Service for generating text embeddings using Sentence Transformers."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """Initialize the embedding service."""
        self.model_name = model_name
        self._model: Optional[SentenceTransformer] = None
    
    @property
    def model(self) -> SentenceTransformer:
        """Get or load the embedding model."""
        if self._model is None:
            try:
                logger.info(f"Loading embedding model: {self.model_name}")
                self._model = SentenceTransformer(self.model_name)
                logger.info("Embedding model loaded successfully")
            except Exception as exc:
                logger.error("Failed to load embedding model", error=str(exc))
                raise ExternalAPIError(f"Failed to load embedding model: {str(exc)}") from exc
        return self._model
    
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Input text
            
        Returns:
            Embedding vector as list of floats
        """
        try:
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                None,
                self.model.encode,
                text
            )
            
            return embedding.tolist()
            
        except Exception as exc:
            logger.error("Failed to generate embedding", text=text[:100], error=str(exc))
            raise ExternalAPIError(f"Embedding generation failed: {str(exc)}") from exc
    
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of input texts
            
        Returns:
            List of embedding vectors
        """
        try:
            if not texts:
                return []
            
            # Run in thread pool for better performance
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                None,
                self.model.encode,
                texts
            )
            
            return embeddings.tolist()
            
        except Exception as exc:
            logger.error("Failed to generate embeddings", text_count=len(texts), error=str(exc))
            raise ExternalAPIError(f"Batch embedding generation failed: {str(exc)}") from exc


@lru_cache()
def get_embedding_service() -> EmbeddingService:
    """Get singleton embedding service instance."""
    return EmbeddingService()