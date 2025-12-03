# tests/test_repositories/test_computer_repository.py
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.computer_repository import ComputerRepository

@pytest.mark.asyncio
async def test_create_computer_repo(db_session: AsyncSession):
    """Test crear computer via repository"""
    repo = ComputerRepository(db_session)
    
    computer_data = {
        "name": "Test Computer",
        "hostname": "test-host",
        "ip_address": "192.168.1.100",
        "adspower_api_url": "http://host.docker.internal:50325",
        "adspower_api_key": "0cbbd771ae5f6fad7ff4917bc66c95be",
        "max_profiles": 50
    }
    
    computer = await repo.create(computer_data)
    
    assert computer.id is not None
    assert computer.name == "Test Computer"

@pytest.mark.asyncio
async def test_get_by_name_repo(db_session: AsyncSession):
    """Test obtener computer por nombre"""
    repo = ComputerRepository(db_session)
    
    # Create
    computer_data = {
        "name": "Unique Computer",
        "hostname": "unique-host",
        "ip_address": "192.168.1.100",
        "adspower_api_url": "http://host.docker.internal:50325",
        "adspower_api_key": "0cbbd771ae5f6fad7ff4917bc66c95be",
    }
    
    await repo.create(computer_data)
    await db_session.commit()
    
    # Get by name
    computer = await repo.get_by_name("Unique Computer")
    
    assert computer is not None
    assert computer.name == "Unique Computer"

@pytest.mark.asyncio
async def test_get_available_computers(db_session: AsyncSession):
    """Test obtener computers disponibles"""
    repo = ComputerRepository(db_session)
    
    # Create computer with capacity
    computer_data = {
        "name": "Available Computer",
        "hostname": "available-host",
        "ip_address": "192.168.1.100",
        "adspower_api_url": "http://host.docker.internal:50325",
        "adspower_api_key": "0cbbd771ae5f6fad7ff4917bc66c95be",
        "max_profiles": 50,
        "current_profiles": 10,
        "is_active": True,
        "status": "online"
    }
    
    await repo.create(computer_data)
    await db_session.commit()
    
    # Get available
    computers = await repo.get_available(min_capacity=1)
    
    assert len(computers) >= 1