# app/repositories/proxy_repository.py
from typing import Optional, List
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base import BaseRepository
from app.models.proxy import Proxy, ProxyType, ProxyStatus
from datetime import datetime, timedelta

class ProxyRepository(BaseRepository[Proxy]):
    """Repositorio para Proxies"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(Proxy, db)
    
    async def get_by_session_id(self, session_id: str) -> Optional[Proxy]:
        """Obtiene proxy por session_id"""
        result = await self.db.execute(
            select(Proxy).where(Proxy.session_id == session_id)
        )
        return result.scalar_one_or_none()
    
    async def get_available(
        self,
        proxy_type: Optional[ProxyType] = None,
        country: Optional[str] = None,
        min_success_rate: float = 80.0
    ) -> List[Proxy]:
        """Obtiene proxies disponibles"""
        query = select(Proxy).where(
            Proxy.is_available == True,
            Proxy.status == ProxyStatus.ACTIVE,
            Proxy.success_rate >= min_success_rate
        )
        
        if proxy_type:
            query = query.where(Proxy.proxy_type == proxy_type)
        
        if country:
            query = query.where(Proxy.country == country)
        
        query = query.order_by(Proxy.success_rate.desc(), Proxy.profiles_count.asc())
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def update_health_check(self, id: int, check_result: dict) -> bool:
        """Actualiza métricas de health check"""
        proxy = await self.get(id)
        if not proxy:
            return False
        
        total_checks = proxy.total_checks + 1
        failed_checks = proxy.failed_checks + (0 if check_result['success'] else 1)
        success_rate = ((total_checks - failed_checks) / total_checks) * 100
        
        update_data = {
            'last_check_at': datetime.utcnow(),
            'total_checks': total_checks,
            'failed_checks': failed_checks,
            'success_rate': success_rate,
        }
        
        if check_result['success']:
            update_data.update({
                'last_success_at': datetime.utcnow(),
                'status': ProxyStatus.ACTIVE,
                'detected_ip': check_result.get('ip'),
                'detected_country': check_result.get('country'),
                'detected_city': check_result.get('city'),
                'detected_isp': check_result.get('isp'),
                'avg_response_time': check_result.get('response_time_ms')
            })
        else:
            # Si falla 3 veces seguidas, marcar como failed
            if failed_checks >= 3:
                update_data['status'] = ProxyStatus.FAILED
                update_data['is_available'] = False
        
        await self.update(id, update_data)
        return True
    
    async def increment_usage(self, id: int) -> bool:
        """Incrementa contador de uso"""
        proxy = await self.get(id)
        if proxy:
            await self.update(id, {
                'profiles_count': proxy.profiles_count + 1,
                'last_used_at': datetime.utcnow()
            })
            return True
        return False
    
    async def get_needing_check(self, minutes: int = 5) -> List[Proxy]:
        """Obtiene proxies que necesitan health check"""
        threshold = datetime.utcnow() - timedelta(minutes=minutes)
        
        result = await self.db.execute(
            select(Proxy).where(
                and_(
                    Proxy.is_available == True,
                    (Proxy.last_check_at.is_(None) | (Proxy.last_check_at < threshold))
                )
            ).limit(50)
        )
        return list(result.scalars().all())
    
    async def get_stats(self) -> dict:
        """Obtiene estadísticas de proxies"""
        result = await self.db.execute(
            select(
                func.count(Proxy.id).label('total'),
                func.count(Proxy.id).filter(Proxy.status == ProxyStatus.ACTIVE).label('active'),
                func.count(Proxy.id).filter(Proxy.proxy_type == ProxyType.MOBILE).label('mobile'),
                func.count(Proxy.id).filter(Proxy.proxy_type == ProxyType.RESIDENTIAL).label('residential'),
                func.avg(Proxy.success_rate).label('avg_success_rate')
            )
        )
        row = result.one()
        return {
            'total': row.total or 0,
            'active': row.active or 0,
            'mobile': row.mobile or 0,
            'residential': row.residential or 0,
            'avg_success_rate': round(row.avg_success_rate or 0, 2)
        }