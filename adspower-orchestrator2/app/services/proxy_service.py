from typing import List, Optional, Dict, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.repositories.proxy_repository import ProxyRepository
from app.integrations.soax_client import SOAXClient
from app.models.proxy import Proxy, ProxyType, ProxyStatus
from app.models.profile import Profile                          # ← AGREGAR
from app.models.proxy_health import ProxyScore                  # ← verificar que esté
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
        status: Optional[str] = None,
        proxy_type: Optional[str] = None,  # ← este faltaba
    ) -> Tuple[List[Proxy], int]:
        from sqlalchemy import func, and_
        conditions = []
        if status:     conditions.append(Proxy.status == status)
        if proxy_type: conditions.append(Proxy.proxy_type == proxy_type)

        query = select(Proxy)
        count_query = select(func.count()).select_from(Proxy)

        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))

        total = (await self.db.execute(count_query)).scalar()
        items = list((await self.db.execute(query.offset(skip).limit(limit))).scalars().all())
        return items, total
    async def _update_proxy_score(
        self,
        proxy_id: int,
        overall_score: float,
        details: Dict
    ):
        """Actualiza score del proxy"""
        
        # Buscar score existente
        result = await self.db.execute(
            select(ProxyScore).where(ProxyScore.proxy_id == proxy_id)
        )
        score_record = result.scalar_one_or_none()
        
        if not score_record:
            # Crear nuevo con valores iniciales
            score_record = ProxyScore(
                proxy_id=proxy_id,
                total_checks=0,
                successful_checks=0,
                failed_checks=0,
                timeout_checks=0,
                geo_mismatch_count=0,
                consecutive_failures=0
            )
            self.db.add(score_record)
        
        # Actualizar scores
        score_record.overall_score = overall_score
        
        # Actualizar estadísticas (con valores por defecto si son None)
        score_record.total_checks = (score_record.total_checks or 0) + 1
    
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