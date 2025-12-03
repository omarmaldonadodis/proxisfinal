# app/services/computer_service.py
from typing import List, Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.computer_repository import ComputerRepository
from app.integrations.adspower_client import AdsPowerClient
from app.models.computer import Computer, ComputerStatus
from app.schemas.computer import ComputerCreate, ComputerUpdate
from loguru import logger
from datetime import datetime

class ComputerService:
    """Servicio para gestión de Computers"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ComputerRepository(db)
    
    async def create_computer(self, computer_in: ComputerCreate) -> Computer:
        """Crea un nuevo computer"""
        # Verificar que el nombre no exista
        existing = await self.repo.get_by_name(computer_in.name)
        if existing:
            raise ValueError(f"Computer with name '{computer_in.name}' already exists")
        
        # Verificar conexión con AdsPower
        client = AdsPowerClient(computer_in.adspower_api_url, computer_in.adspower_api_key)
        if not await client.test_connection():
            raise ValueError("Cannot connect to AdsPower API. Check URL and API Key.")
        
        # Crear computer
        computer_data = computer_in.model_dump()
        computer_data['status'] = ComputerStatus.ONLINE
        computer_data['last_seen_at'] = datetime.utcnow()
        
        computer = await self.repo.create(computer_data)
        await self.db.commit()
        
        logger.info(f"Computer created: {computer.name} (ID: {computer.id})")
        return computer
    
    async def get_computer(self, computer_id: int) -> Optional[Computer]:
        """Obtiene computer por ID"""
        return await self.repo.get(computer_id)
    
    async def list_computers(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[ComputerStatus] = None,
        is_active: Optional[bool] = None
    ) -> tuple[List[Computer], int]:
        """Lista computers con filtros"""
        filters = {}
        if status:
            filters['status'] = status
        if is_active is not None:
            filters['is_active'] = is_active
        
        computers = await self.repo.get_multi(skip=skip, limit=limit, filters=filters, order_by='-created_at')
        total = await self.repo.count(filters=filters)
        
        return computers, total
    
    async def update_computer(self, computer_id: int, computer_in: ComputerUpdate) -> Optional[Computer]:
        """Actualiza computer"""
        computer = await self.repo.get(computer_id)
        if not computer:
            raise ValueError(f"Computer {computer_id} not found")
        
        # Si se actualizan credenciales, verificar conexión
        if computer_in.adspower_api_url or computer_in.adspower_api_key:
            api_url = computer_in.adspower_api_url or computer.adspower_api_url
            api_key = computer_in.adspower_api_key or computer.adspower_api_key
            
            client = AdsPowerClient(api_url, api_key)
            if not await client.test_connection():
                raise ValueError("Cannot connect to AdsPower API with provided credentials")
        
        update_data = computer_in.model_dump(exclude_unset=True)
        computer = await self.repo.update(computer_id, update_data)
        await self.db.commit()
        
        logger.info(f"Computer updated: {computer.name}")
        return computer
    
    async def delete_computer(self, computer_id: int) -> bool:
        """Elimina computer"""
        computer = await self.repo.get(computer_id)
        if not computer:
            raise ValueError(f"Computer {computer_id} not found")
        
        # Verificar que no tenga perfiles activos
        if computer.current_profiles > 0:
            raise ValueError(f"Cannot delete computer with {computer.current_profiles} active profiles")
        
        success = await self.repo.delete(computer_id)
        await self.db.commit()
        
        logger.info(f"Computer deleted: {computer.name}")
        return success
    
    async def get_available_computers(self, min_capacity: int = 1) -> List[Computer]:
        """Obtiene computers disponibles"""
        return await self.repo.get_available(min_capacity=min_capacity)
    
    async def health_check(self, computer_id: int) -> Dict:
        """Verifica salud de un computer"""
        computer = await self.repo.get(computer_id)
        if not computer:
            raise ValueError(f"Computer {computer_id} not found")
        
        # Verificar conexión AdsPower
        client = AdsPowerClient(computer.adspower_api_url, computer.adspower_api_key)
        
        health = {
            'computer_id': computer_id,
            'name': computer.name,
            'is_healthy': False,
            'adspower_connected': False,
            'current_profiles': computer.current_profiles,
            'max_profiles': computer.max_profiles,
            'capacity_percentage': (computer.current_profiles / computer.max_profiles * 100) if computer.max_profiles > 0 else 0
        }
        
        try:
            health['adspower_connected'] = await client.test_connection()
            
            if health['adspower_connected']:
                # Actualizar status
                await self.repo.update(computer_id, {
                    'status': ComputerStatus.ONLINE,
                    'last_seen_at': datetime.utcnow()
                })
                health['is_healthy'] = True
            else:
                await self.repo.update(computer_id, {'status': ComputerStatus.OFFLINE})
        
        except Exception as e:
            logger.error(f"Health check failed for computer {computer_id}: {e}")
            await self.repo.update(computer_id, {'status': ComputerStatus.ERROR})
            health['error'] = str(e)
        
        await self.db.commit()
        return health
    
    async def get_stats(self) -> Dict:
        """Obtiene estadísticas generales"""
        return await self.repo.get_stats()