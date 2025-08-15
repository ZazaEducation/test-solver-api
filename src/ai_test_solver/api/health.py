"""Health check endpoints."""

from fastapi import APIRouter, Depends
from ..core import get_logger, settings
from ..models.api import HealthResponse
from ..services import DatabaseService, get_database_service

router = APIRouter()
logger = get_logger(__name__)


@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check(db: DatabaseService = Depends(get_database_service)):
    """
    Health check endpoint that verifies system status.
    
    Returns:
        Health status including database connectivity and external services
    """
    # Check database connection
    database_connected = await db.health_check()
    
    # Check external services (simplified for now)
    external_services = {
        "openai": True,  # TODO: Implement actual health checks
        "google_cloud_vision": True,
        "google_custom_search": True,
        "supabase": database_connected,
    }
    
    # Determine overall status
    all_healthy = database_connected and all(external_services.values())
    status = "healthy" if all_healthy else "degraded"
    
    logger.info(
        "Health check completed",
        status=status,
        database_connected=database_connected,
        external_services=external_services,
    )
    
    return HealthResponse(
        status=status,
        version="0.1.0",
        environment=settings.environment,
        database_connected=database_connected,
        external_services=external_services,
        message="Health check completed" if all_healthy else "Some services are unavailable"
    )