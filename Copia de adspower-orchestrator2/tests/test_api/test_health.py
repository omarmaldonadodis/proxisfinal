# tests/test_api/test_health.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test health check básico"""
    response = await client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

@pytest.mark.asyncio
async def test_system_health(client: AsyncClient):
    """Test health check del sistema"""
    response = await client.get("/api/v1/health/system")
    
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "components" in data

@pytest.mark.asyncio
async def test_database_health(client: AsyncClient):
    """Test health check de database"""
    response = await client.get("/api/v1/health/database")
    
    assert response.status_code == 200
    data = response.json()
    assert "healthy" in data