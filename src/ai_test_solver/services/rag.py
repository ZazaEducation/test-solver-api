"""RAG (Retrieval-Augmented Generation) service combining knowledge base and web search."""

import asyncio
from typing import List, Dict, Any, Optional
from functools import lru_cache

import httpx

from ..core import get_logger, settings, RAGError
from ..models.knowledge import KnowledgeSearchResult
from .embedding import EmbeddingService, get_embedding_service
from .database import DatabaseService, get_database_service

logger = get_logger(__name__)


class RAGService:
    """Service for Retrieval-Augmented Generation using knowledge base and web search."""
    
    def __init__(
        self,
        embedding_service: Optional[EmbeddingService] = None,
        db_service: Optional[DatabaseService] = None
    ):
        """Initialize the RAG service."""
        self.embedding = embedding_service or get_embedding_service()
        self.db = db_service or get_database_service()
        self.http_client = httpx.AsyncClient(timeout=30.0)
    
    async def get_context_for_question(
        self,
        question: str,
        question_type: Optional[str] = None,
        max_results: int = 5
    ) -> str:
        """
        Get relevant context for a question using both knowledge base and web search.
        
        Args:
            question: The question text
            question_type: Type of question (optional)
            max_results: Maximum number of results to retrieve
            
        Returns:
            Combined context string
        """
        try:
            logger.info(
                "Getting RAG context for question",
                question=question[:100],
                question_type=question_type,
                max_results=max_results
            )
            
            # Run knowledge base search and web search concurrently
            knowledge_task = self._search_knowledge_base(question, max_results)
            web_search_task = self._search_web(question, max_results)
            
            knowledge_results, web_results = await asyncio.gather(
                knowledge_task,
                web_search_task,
                return_exceptions=True
            )
            
            # Handle exceptions
            if isinstance(knowledge_results, Exception):
                logger.warning("Knowledge base search failed", error=str(knowledge_results))
                knowledge_results = []
            
            if isinstance(web_results, Exception):
                logger.warning("Web search failed", error=str(web_results))
                web_results = []
            
            # Combine results into context
            context_parts = []
            
            # Add knowledge base results
            if knowledge_results:
                context_parts.append("KNOWLEDGE BASE:")
                for result in knowledge_results:
                    context_parts.append(f"- {result['title']}: {result['content'][:200]}...")
                context_parts.append("")
            
            # Add web search results
            if web_results:
                context_parts.append("WEB SEARCH RESULTS:")
                for result in web_results:
                    context_parts.append(f"- {result['title']}: {result['snippet']}")
                context_parts.append("")
            
            combined_context = "\n".join(context_parts)
            
            logger.info(
                "RAG context generated",
                knowledge_results=len(knowledge_results) if isinstance(knowledge_results, list) else 0,
                web_results=len(web_results) if isinstance(web_results, list) else 0,
                context_length=len(combined_context)
            )
            
            return combined_context
            
        except Exception as exc:
            logger.error("RAG context generation failed", error=str(exc), exc_info=True)
            raise RAGError(f"Failed to generate context: {str(exc)}") from exc
    
    async def _search_knowledge_base(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Search the knowledge base using vector similarity.
        
        Args:
            query: Search query
            max_results: Maximum results to return
            
        Returns:
            List of search results
        """
        try:
            # Generate query embedding
            query_embedding = await self.embedding.generate_embedding(query)
            
            # Search knowledge base (using raw SQL for now since we need pgvector)
            search_query = """
                SELECT id, title, content, source_url, category,
                       1 - (embedding <=> $1::vector) AS similarity
                FROM knowledge_base
                WHERE 1 - (embedding <=> $1::vector) > $2
                ORDER BY embedding <=> $1::vector
                LIMIT $3
            """
            
            async with self.db._db_pool.acquire() as conn:
                records = await conn.fetch(
                    search_query,
                    query_embedding,
                    settings.vector_similarity_threshold,
                    max_results
                )
            
            results = []
            for record in records:
                results.append({
                    'id': str(record['id']),
                    'title': record['title'],
                    'content': record['content'],
                    'source_url': record['source_url'],
                    'category': record['category'],
                    'similarity': float(record['similarity'])
                })
            
            logger.info(f"Knowledge base search returned {len(results)} results")
            return results
            
        except Exception as exc:
            logger.error("Knowledge base search failed", error=str(exc))
            # Return empty results instead of failing the entire RAG process
            return []
    
    async def _search_web(self, query: str, max_results: int = 3) -> List[Dict[str, Any]]:
        """
        Search the web using Google Custom Search API.
        
        Args:
            query: Search query
            max_results: Maximum results to return
            
        Returns:
            List of search results
        """
        try:
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                'key': settings.google_custom_search_api_key,
                'cx': settings.google_custom_search_engine_id,
                'q': query,
                'num': min(max_results, 10),  # API max is 10
                'safe': 'active',
                'fields': 'items(title,link,snippet)'
            }
            
            response = await self.http_client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            items = data.get('items', [])
            
            results = []
            for item in items:
                results.append({
                    'title': item.get('title', ''),
                    'url': item.get('link', ''),
                    'snippet': item.get('snippet', '')
                })
            
            logger.info(f"Web search returned {len(results)} results")
            return results
            
        except Exception as exc:
            logger.error("Web search failed", error=str(exc))
            # Return empty results instead of failing the entire RAG process
            return []
    
    async def add_knowledge(
        self,
        title: str,
        content: str,
        source_url: Optional[str] = None,
        category: Optional[str] = None
    ) -> bool:
        """
        Add knowledge to the knowledge base.
        
        Args:
            title: Title of the knowledge entry
            content: Content text
            source_url: Optional source URL
            category: Optional category
            
        Returns:
            True if successful
        """
        try:
            # Generate embedding for the content
            embedding = await self.embedding.generate_embedding(content)
            
            # Insert into database
            query = """
                INSERT INTO knowledge_base (title, content, source_url, category, embedding)
                VALUES ($1, $2, $3, $4, $5)
            """
            
            async with self.db._db_pool.acquire() as conn:
                await conn.execute(query, title, content, source_url, category, embedding)
            
            logger.info("Knowledge added to database", title=title, category=category)
            return True
            
        except Exception as exc:
            logger.error("Failed to add knowledge", error=str(exc))
            return False
    
    async def close(self):
        """Close HTTP client."""
        await self.http_client.aclose()


@lru_cache()
def get_rag_service() -> RAGService:
    """Get singleton RAG service instance."""
    return RAGService()