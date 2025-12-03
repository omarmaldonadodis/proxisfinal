# app/services/proxy_service.py
from typing import List, Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.proxy_repository import ProxyRepository
from app.integrations.soax_client import SOAXClient
from app.models.proxy import Proxy, ProxyType, ProxyStatus
from app.schemas.proxy import ProxyCreate, ProxyUpdate
from app.config import settings
from loguru import logger

class ProxyService:
    """Servicio para gestión de Proxies"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ProxyRepository(db)
        self.soax = SOAXClient(
            username=settings.SOAX_USERNAME,
            password=settings.SOAX_PASSWORD,
            host=settings.SOAX_HOST,
            port=settings.SOAX_PORT
        )
    
    async def create_proxy(self, proxy_in: ProxyCreate) -> Proxy:
        """Crea un nuevo proxy"""
        # Generar configuración SOAX
        proxy_config = self.soax.get_proxy_config(
            proxy_type=proxy_in.proxy_type.value,
            country=proxy_in.country,
            city=proxy_in.city,
            region=proxy_in.region,
            session_lifetime=proxy_in.session_lifetime
        )
        
        # Probar proxy
        test_result = await self.soax.test_proxy(proxy_config, timeout=30)
        
        # Crear proxy en DB
        proxy_data = proxy_in.model_dump()
        proxy_data.update({
            'session_id': proxy_config['session_id'],
            'username': proxy_config['username'],
            'password': proxy_config['password'],
            'status': ProxyStatus.ACTIVE if test_result['success'] else ProxyStatus.FAILED,
            'is_available': test_result['success'],
            'detected_ip': test_result.get('ip'),
            'detected_country': test_result.get('country'),
            'detected_city': test_result.get('city'),
            'detected_isp': test_result.get('isp'),
            'avg_response_time': test_result.get('response_time_ms'),
            'total_checks': 1,
            'failed_checks': 0 if test_result['success'] else 1,
            'success_rate': 100.0 if test_result['success'] else 0.0
        })
        
        proxy = await self.repo.create(proxy_data)
        await self.db.commit()
        
        logger.info(f"Proxy created: {proxy.proxy_type} {proxy.country} (ID: {proxy.id})")
        return proxy
    
    async def get_proxy(self, proxy_id: int) -> Optional[Proxy]:
        """Obtiene proxy por ID"""
        return await self.repo.get(proxy_id)
    
    async def list_proxies(
        self,
        skip: int = 0,
        limit: int = 100,
        proxy_type: Optional[ProxyType] = None,
        country: Optional[str] = None,
        status: Optional[ProxyStatus] = None
    ) -> tuple[List[Proxy], int]:
        """Lista proxies con filtros"""
        filters = {}
        if proxy_type:
            filters['proxy_type'] = proxy_type
        if country:
            filters['country'] = country
        if status:
            filters['status'] = status
        
        proxies = await self.repo.get_multi(skip=skip, limit=limit, filters=filters, order_by='-created_at')
        total = await self.repo.count(filters=filters)
        
        return proxies, total
    
    async def update_proxy(self, proxy_id: int, proxy_in: ProxyUpdate) -> Optional[Proxy]:
        """Actualiza proxy"""
        proxy = await self.repo.get(proxy_id)
        if not proxy:
            raise ValueError(f"Proxy {proxy_id} not found")
        
        update_data = proxy_in.model_dump(exclude_unset=True)
        proxy = await self.repo.update(proxy_id, update_data)
        await self.db.commit()
        
        logger.info(f"Proxy updated: {proxy_id}")
        return proxy
    
    async def delete_proxy(self, proxy_id: int) -> bool:
        """Elimina proxy"""
        proxy = await self.repo.get(proxy_id)
        if not proxy:
            raise ValueError(f"Proxy {proxy_id} not found")
        
        # Verificar que no esté en uso
        if proxy.profiles_count > 0:
            raise ValueError(f"Cannot delete proxy with {proxy.profiles_count} profiles using it")
        
        success = await self.repo.delete(proxy_id)
        await self.db.commit()
        
        logger.info(f"Proxy deleted: {proxy_id}")
        return success
    
    async def test_proxy(self, proxy_id: int) -> Dict:
        """Prueba un proxy"""
        proxy = await self.repo.get(proxy_id)
        if not proxy:
            raise ValueError(f"Proxy {proxy_id} not found")
        
        # Configurar proxy
        proxy_config = {
            'type': 'http',
            'host': proxy.host,
            'port': proxy.port,
            'username': proxy.username,
            'password': proxy.password
        }
        
        # Probar
        result = await self.soax.test_proxy(proxy_config, timeout=30)
        
        # Actualizar health check
        await self.repo.update_health_check(proxy_id, result)
        await self.db.commit()
        
        return result
    
    async def get_available_proxy(
        self,
        proxy_type: Optional[ProxyType] = None,
        country: Optional[str] = None
    ) -> Optional[Proxy]:
        """Obtiene un proxy disponible"""
        proxies = await self.repo.get_available(
            proxy_type=proxy_type,
            country=country,
            min_success_rate=80.0
        )
        
        if proxies:
            return proxies[0]
        return None
    
    async def health_check_batch(self, limit: int = 50) -> Dict:
        """Health check en batch"""
        proxies = await self.repo.get_needing_check(minutes=5)
        
        results = {
            'total': len(proxies),
            'success': 0,
            'failed': 0
        }
        
        for proxy in proxies[:limit]:
            try:
                result = await self.test_proxy(proxy.id)
                if result['success']:
                    results['success'] += 1
                else:
                    results['failed'] += 1
            except Exception as e:
                logger.error(f"Error checking proxy {proxy.id}: {e}")
                results['failed'] += 1
        
        return results
    
    async def get_stats(self) -> Dict:
        """Obtiene estadísticas de proxies"""
        return await self.repo.get_stats()