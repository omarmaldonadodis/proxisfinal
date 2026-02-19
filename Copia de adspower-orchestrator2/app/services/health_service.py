# app/services/health_service.py
from typing import Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.services.computer_service import ComputerService
from app.services.proxy_service import ProxyService
from loguru import logger
import redis
from app.config import settings

class HealthService:
    """Servicio para health checks del sistema"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def check_system_health(self) -> Dict:
        """Health check completo del sistema"""
        health = {
            'status': 'healthy',
            'components': {}
        }
        
        # Database
        db_health = await self.check_database()
        health['components']['database'] = db_health
        if not db_health['healthy']:
            health['status'] = 'unhealthy'
        
        # Redis
        redis_health = await self.check_redis()
        health['components']['redis'] = redis_health
        if not redis_health['healthy']:
            health['status'] = 'unhealthy'
        
        # Computers
        computers_health = await self.check_all_computers()
        health['components']['computers'] = computers_health
        
        # Proxies
        proxies_health = await self.check_proxies()
        health['components']['proxies'] = proxies_health
        
        return health
    
    async def check_database(self) -> Dict:
        """Verifica salud de la base de datos"""
        try:
            result = await self.db.execute(text("SELECT 1"))
            result.scalar()
            
            return {
                'healthy': True,
                'message': 'Database connection OK'
            }
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                'healthy': False,
                'error': str(e)
            }
    
    async def check_redis(self) -> Dict:
        """Verifica salud de Redis"""
        try:
            r = redis.from_url(settings.REDIS_URL)
            r.ping()
            r.close()
            
            return {
                'healthy': True,
                'message': 'Redis connection OK'
            }
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {
                'healthy': False,
                'error': str(e)
            }
    
    async def check_all_computers(self) -> Dict:
        """Health check de todos los computers"""
        service = ComputerService(self.db)
        stats = await service.get_stats()
        
        return {
            'total': stats['total'],
            'online': stats['online'],
            'offline': stats['offline'],
            'health_percentage': (stats['online'] / stats['total'] * 100) if stats['total'] > 0 else 0
        }
    
    async def check_proxies(self) -> Dict:
        """Health check de proxies"""
        service = ProxyService(self.db)
        stats = await service.get_stats()
        
        return {
            'total': stats['total'],
            'active': stats['active'],
            'avg_success_rate': stats['avg_success_rate']
        }