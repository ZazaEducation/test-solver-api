"""Test health endpoints."""

import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient

from src.ai_test_solver.main import app


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] is True
    assert "status" in data
    assert "version" in data
    assert "environment" in data
    assert "database_connected" in data
    assert "external_services" in data


@pytest.mark.asyncio
async def test_health_endpoint_async():
    """Test health check endpoint with async client."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "status" in data