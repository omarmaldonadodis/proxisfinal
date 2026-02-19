# tests/test_services/test_computer_service.py
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.computer_service import ComputerService
from app.schemas.computer import ComputerCreate

@pytest.mark.asyncio
async def test_create_computer_service(db_session: AsyncSession):
    """Test crear computer via service"""
    service = ComputerService(db_session)
    
    computer_in = ComputerCreate(
        name="Test Computer",
        hostname="test-host",
        ip_address="192.168.1.100",
        adspower_api_url="http://localhost:50325",
        adspower_api_key="test-key",
        max_profiles=50
    )
    
    computer = await service.create_computer(computer_in)
    
    assert computer.id is not None
    assert computer.name == "Test Computer"
    assert computer.max_profiles == 50

@pytest.mark.asyncio
async def test_get_computer_service(db_session: AsyncSession):
    """Test obtener computer via service"""
    service = ComputerService(db_session)
    
    # Create
    computer_in = ComputerCreate(
        name="Test Computer",
        hostname="test-host",
        ip_address="192.168.1.100",
        adspower_api_url="http://localhost:50325",
        adspower_api_key="test-key"
    )
    
    created = await service.create_computer(computer_in)
    
    # Get
    computer = await service.get_computer(created.id)
    
    assert computer is not None
    assert computer.id == created.id

@pytest.mark.asyncio
async def test_list_computers_service(db_session: AsyncSession):
    """Test listar computers via service"""
    service = ComputerService(db_session)
    
    # Create multiple
    for i in range(3):
        computer_in = ComputerCreate(
            name=f"Test Computer {i}",
            hostname=f"test-host-{i}",
            ip_address=f"192.168.1.{100+i}",
            adspower_api_url="http://localhost:50325",
            adspower_api_key="test-key"
        )
        await service.create_computer(computer_in)
    
    # List
    computers, total = await service.list_computers(limit=10)
    
    assert total >= 3
    assert len(computers) >= 3