# app/repositories/profile_repository.py
from typing import Optional, List
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.repositories.base import BaseRepository
from app.models.profile import Profile, ProfileStatus
from datetime import datetime

class ProfileRepository(BaseRepository[Profile]):
    """Repositorio para Profiles"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(Profile, db)
    
    async def get_by_adspower_id(self, adspower_id: str) -> Optional[Profile]:
        """Obtiene profile por adspower_id"""
        result = await self.db.execute(
            select(Profile).where(Profile.adspower_id == adspower_id)
        )
        return result.scalar_one_or_none()
    
    async def get_with_relations(self, id: int) -> Optional[Profile]:
        """Obtiene profile con relaciones cargadas"""
        result = await self.db.execute(
            select(Profile)
            .options(
                selectinload(Profile.computer),
                selectinload(Profile.proxy)
            )
            .where(Profile.id == id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_computer(self, computer_id: int) -> List[Profile]:
        """Obtiene profiles de un computer específico"""
        result = await self.db.execute(
            select(Profile).where(Profile.computer_id == computer_id)
        )
        return list(result.scalars().all())
    
    async def get_available_for_automation(self, limit: int = 10) -> List[Profile]:
        """Obtiene profiles disponibles para automatización"""
        result = await self.db.execute(
            select(Profile)
            .options(selectinload(Profile.computer))
            .where(
                Profile.status.in_([ProfileStatus.READY, ProfileStatus.ACTIVE]),
                Profile.is_warmed == True
            )
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def update_status(self, id: int, status: ProfileStatus) -> bool:
        """Actualiza estado del profile"""
        return await self.update(id, {'status': status})
    
    async def mark_as_warmed(self, id: int) -> bool:
        """Marca profile como warmed"""
        return await self.update(id, {
            'is_warmed': True,
            'warmup_completed_at': datetime.utcnow()
        })
    
    async def increment_session(self, id: int, duration_seconds: int) -> bool:
        """Incrementa contador de sesiones"""
        profile = await self.get(id)
        if profile:
            await self.update(id, {
                'total_sessions': profile.total_sessions + 1,
                'total_duration_seconds': profile.total_duration_seconds + duration_seconds,
                'last_opened_at': datetime.utcnow()
            })
            return True
        return False
    
    async def get_stats(self) -> dict:
        """Obtiene estadísticas de profiles"""
        result = await self.db.execute(
            select(
                func.count(Profile.id).label('total'),
                func.count(Profile.id).filter(Profile.status == ProfileStatus.READY).label('ready'),
                func.count(Profile.id).filter(Profile.status == ProfileStatus.ACTIVE).label('active'),
                func.count(Profile.id).filter(Profile.is_warmed == True).label('warmed'),
                func.sum(Profile.total_sessions).label('total_sessions')
            )
        )
        row = result.one()
        return {
            'total': row.total or 0,
            'ready': row.ready or 0,
            'active': row.active or 0,
            'warmed': row.warmed or 0,
            'total_sessions': row.total_sessions or 0
        }