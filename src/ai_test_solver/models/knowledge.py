"""Knowledge base and RAG-related data models."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class KnowledgeBaseEntry(BaseModel):
    """Model for knowledge base entries."""
    id: Optional[UUID] = None
    title: str = Field(..., min_length=1, max_length=500, description="Title of the knowledge entry")
    content: str = Field(..., min_length=1, description="Content of the knowledge entry")
    source_url: Optional[str] = Field(None, description="Source URL if available")
    category: Optional[str] = Field(None, description="Category of the knowledge")
    created_date: Optional[datetime] = None
    updated_date: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class KnowledgeSearchResult(BaseModel):
    """Model for knowledge base search results."""
    id: UUID
    title: str
    content: str
    source_url: Optional[str] = None
    category: Optional[str] = None
    similarity: float = Field(..., ge=0.0, le=1.0, description="Similarity score")


class EmbeddingRequest(BaseModel):
    """Model for embedding generation requests."""
    text: str = Field(..., min_length=1, description="Text to generate embeddings for")
    model: str = Field(default="all-MiniLM-L6-v2", description="Embedding model to use")


class EmbeddingResponse(BaseModel):
    """Model for embedding generation responses."""
    embedding: List[float] = Field(..., description="Generated embedding vector")
    model: str = Field(..., description="Model used for embedding generation")
    text_length: int = Field(..., description="Length of input text")


class RAGContext(BaseModel):
    """Model for RAG context information."""
    knowledge_results: List[KnowledgeSearchResult] = Field(
        default_factory=list,
        description="Results from knowledge base search"
    )
    web_results: List[dict] = Field(
        default_factory=list,
        description="Results from web search"
    )
    total_context_length: int = Field(default=0, description="Total context length in characters")


class RAGRequest(BaseModel):
    """Model for RAG processing requests."""
    query: str = Field(..., min_length=1, description="Query text for RAG")
    question_type: Optional[str] = Field(None, description="Type of question for context")
    max_results: int = Field(default=5, ge=1, le=20, description="Maximum results to return")
    similarity_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum similarity threshold"
    )


class RAGResponse(BaseModel):
    """Model for RAG processing responses."""
    context: RAGContext
    generated_answer: Optional[str] = Field(None, description="Generated answer using RAG")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Confidence score")
    processing_time: float = Field(..., ge=0, description="Processing time in seconds")