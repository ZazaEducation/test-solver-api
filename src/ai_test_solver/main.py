"""Main FastAPI application."""

import time
from contextlib import asynccontextmanager
from typing import Dict, Any
from uuid import uuid4

import uvicorn
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, Response
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

from .api import health, tests
from .core import setup_logging, get_logger, settings, TestSolverException
from .services import DatabaseService, get_database_service

# Setup logging
setup_logging()
logger = get_logger(__name__)

# Metrics
REQUEST_COUNT = Counter(
    'http_requests_total', 
    'Total HTTP requests', 
    ['method', 'endpoint', 'status_code']
)
REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting AI Test Solver API", version=app.version)
    
    # Initialize database connection
    db_service = get_database_service()
    await db_service.connect()
    logger.info("Database connection established")
    
    # Initialize other services
    # TODO: Initialize embedding service, RAG service, etc.
    
    yield
    
    # Shutdown
    logger.info("Shutting down AI Test Solver API")
    await db_service.disconnect()
    logger.info("Database connection closed")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    app = FastAPI(
        title="AI Test Solver API",
        description="Intelligent test solving API with OCR, RAG, and concurrent processing",
        version="0.1.0",
        docs_url="/docs" if settings.is_development() else None,
        redoc_url="/redoc" if settings.is_development() else None,
        openapi_url="/openapi.json" if settings.is_development() else None,
        lifespan=lifespan,
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.is_development() else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Trusted host middleware for production
    if settings.is_production():
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["*.googleapis.com", "*.supabase.co", "localhost"]
        )
    
    # Request middleware for logging and metrics
    @app.middleware("http")
    async def request_middleware(request: Request, call_next):
        """Add request ID, logging, and metrics."""
        # Generate request ID
        request_id = str(uuid4())
        request.state.request_id = request_id
        
        # Add request context to logging
        logger = get_logger(__name__).bind(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            user_agent=request.headers.get("user-agent"),
        )
        
        start_time = time.time()
        
        try:
            # Process request
            response = await call_next(request)
            
            # Record metrics
            duration = time.time() - start_time
            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=request.url.path,
                status_code=response.status_code
            ).inc()
            REQUEST_DURATION.labels(
                method=request.method,
                endpoint=request.url.path
            ).observe(duration)
            
            # Log response
            logger.info(
                "Request completed",
                status_code=response.status_code,
                duration=duration,
            )
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as exc:
            # Record error metrics
            duration = time.time() - start_time
            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=request.url.path,
                status_code=500
            ).inc()
            REQUEST_DURATION.labels(
                method=request.method,
                endpoint=request.url.path
            ).observe(duration)
            
            # Log error
            logger.error(
                "Request failed",
                error=str(exc),
                duration=duration,
                exc_info=True,
            )
            
            raise
    
    # Exception handlers
    @app.exception_handler(TestSolverException)
    async def test_solver_exception_handler(request: Request, exc: TestSolverException):
        """Handle custom application exceptions."""
        logger.error(
            "Application error",
            error_code=exc.error_code,
            message=exc.message,
            details=exc.details,
            request_id=getattr(request.state, 'request_id', None),
        )
        
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "success": False,
                "message": exc.message,
                "error_code": exc.error_code,
                "details": exc.details,
                "request_id": getattr(request.state, 'request_id', None),
            }
        )
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions."""
        logger.warning(
            "HTTP error",
            status_code=exc.status_code,
            detail=exc.detail,
            request_id=getattr(request.state, 'request_id', None),
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "message": exc.detail,
                "error_code": f"HTTP_{exc.status_code}",
                "request_id": getattr(request.state, 'request_id', None),
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle unexpected exceptions."""
        logger.error(
            "Unexpected error",
            error=str(exc),
            request_id=getattr(request.state, 'request_id', None),
            exc_info=True,
        )
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "message": "Internal server error" if settings.is_production() else str(exc),
                "error_code": "INTERNAL_SERVER_ERROR",
                "request_id": getattr(request.state, 'request_id', None),
            }
        )
    
    # Metrics endpoint
    @app.get("/metrics", include_in_schema=False)
    async def metrics():
        """Prometheus metrics endpoint."""
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
    
    # Include routers
    app.include_router(health.router, prefix="/api/v1")
    app.include_router(tests.router, prefix="/api/v1")
    
    return app


# Create the app instance
app = create_app()


# For development
if __name__ == "__main__":
    uvicorn.run(
        "src.ai_test_solver.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.is_development(),
        log_level=settings.log_level.lower(),
    )