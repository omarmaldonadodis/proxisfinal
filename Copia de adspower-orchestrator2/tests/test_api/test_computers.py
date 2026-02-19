# tests/test_api/test_computers.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_computer(client: AsyncClient):
    """Test crear computer"""
    response = await client.post(
        "/api/v1/computers/",
        json={
            "name": "Test Computer",
            "hostname": "test-computer",
            "ip_address": "192.168.1.100",
            "adspower_api_url": "http://localhost:50325",
            "adspower_api_key": "test-key",
            "max_profiles": 50
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Computer"
    assert data["max_profiles"] == 50

@pytest.mark.asyncio
async def test_list_computers(client: AsyncClient):
    """Test listar computers"""
    # Create computer first
    await client.post(
        "/api/v1/computers/",
        json={
            "name": "Test Computer",
            "hostname": "test-computer",
            "ip_address": "192.168.1.100",
            "adspower_api_url": "http://localhost:50325",
            "adspower_api_key": "test-key"
        }
    )
    
    response = await client.get("/api/v1/computers/")
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1

@pytest.mark.asyncio
async def test_get_computer(client: AsyncClient):
    """Test obtener computer por ID"""
    # Create computer
    create_response = await client.post(
        "/api/v1/computers/",
        json={
            "name": "Test Computer",
            "hostname": "test-computer",
            "ip_address": "192.168.1.100",
            "adspower_api_url": "http://localhost:50325",
            "adspower_api_key": "test-key"
        }
    )
    
    computer_id = create_response.json()["id"]
    
    response = await client.get(f"/api/v1/computers/{computer_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == computer_id

@pytest.mark.asyncio
async def test_update_computer(client: AsyncClient):
    """Test actualizar computer"""
    # Create computer
    create_response = await client.post(
        "/api/v1/computers/",
        json={
            "name": "Test Computer",
            "hostname": "test-computer",
            "ip_address": "192.168.1.100",
            "adspower_api_url": "http://localhost:50325",
            "adspower_api_key": "test-key"
        }
    )
    
    computer_id = create_response.json()["id"]
    
    response = await client.patch(
        f"/api/v1/computers/{computer_id}",
        json={"max_profiles": 100}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["max_profiles"] == 100

@pytest.mark.asyncio
async def test_delete_computer(client: AsyncClient):
    """Test eliminar computer"""
    # Create computer
    create_response = await client.post(
        "/api/v1/computers/",
        json={
            "name": "Test Computer",
            "hostname": "test-computer",
            "ip_address": "192.168.1.100",
            "adspower_api_url": "http://localhost:50325",
            "adspower_api_key": "test-key"
        }
    )
    
    computer_id = create_response.json()["id"]
    
    response = await client.delete(f"/api/v1/computers/{computer_id}")
    
    assert response.status_code == 204

@pytest.mark.asyncio
async def test_computer_stats(client: AsyncClient):
    """Test estadísticas de computers"""
    response = await client.get("/api/v1/computers/stats/summary")
    
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "online" in data