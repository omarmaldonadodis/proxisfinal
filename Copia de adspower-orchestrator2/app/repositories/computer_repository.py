# app/repositories/computer_repository.py
from typing import Optional, List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base import BaseRepository
from app.models.computer import Computer, ComputerStatus
from datetime import datetime

class ComputerRepository(BaseRepository[Computer]):
    """Repositorio para Computers"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(Computer, db)
    
    async def get_by_name(self, name: str) -> Optional[Computer]:
        """Obtiene computer por nombre"""
        result = await self.db.execute(
            select(Computer).where(Computer.name == name)
        )
        return result.scalar_one_or_none()
    
    async def get_available(self, min_capacity: int = 1) -> List[Computer]:
        """Obtiene computers con capacidad disponible"""
        result = await self.db.execute(
            select(Computer).where(
                Computer.is_active == True,
                Computer.status == ComputerStatus.ONLINE,
                Computer.current_profiles < Computer.max_profiles - min_capacity
            ).order_by(Computer.current_profiles.asc())
        )
        return list(result.scalars().all())
    
    async def update_last_seen(self, id: int) -> bool:
        """Actualiza last_seen_at"""
        return await self.update(id, {'last_seen_at': datetime.utcnow()})
    
    async def increment_profiles(self, id: int, count: int = 1) -> bool:
        """Incrementa contador de perfiles"""
        computer = await self.get(id)
        if computer:
            new_count = computer.current_profiles + count
            await self.update(id, {'current_profiles': new_count})
            return True
        return False
    
    async def decrement_profiles(self, id: int, count: int = 1) -> bool:
        """Decrementa contador de perfiles"""
        computer = await self.get(id)
        if computer:
            new_count = max(0, computer.current_profiles - count)
            await self.update(id, {'current_profiles': new_count})
            return True
        return False
    
    async def get_stats(self) -> dict:
        """Obtiene estadísticas generales"""
        result = await self.db.execute(
            select(
                func.count(Computer.id).label('total'),
                func.count(Computer.id).filter(Computer.status == ComputerStatus.ONLINE).label('online'),
                func.count(Computer.id).filter(Computer.status == ComputerStatus.OFFLINE).label('offline'),
                func.sum(Computer.current_profiles).label('total_profiles'),
                func.sum(Computer.max_profiles).label('total_capacity')
            )
        )
        row = result.one()
        return {
            'total': row.total or 0,
            'online': row.online or 0,
            'offline': row.offline or 0,
            'total_profiles': row.total_profiles or 0,
            'total_capacity': row.total_capacity or 0
        }