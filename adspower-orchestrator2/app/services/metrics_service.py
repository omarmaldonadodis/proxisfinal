# app/services/metrics_service.py
"""
Servicio para métricas y analytics de profiles y proxies
"""
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from datetime import datetime, timedelta
from loguru import logger

from app.models.profile_metrics import ProfileMetrics, ProxyUsageStats
from app.models.profile import Profile, ProfileStatus
from app.models.proxy import Proxy, ProxyStatus


class MetricsService:
    """Servicio de métricas y analytics"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def record_profile_creation(
        self,
        profile_id: int,
        proxy_id: int,
        creation_duration: float,
        proxy_latency: float,
        device_info: Dict,
        cookies_count: int,
        adspower_response_time: float,
        success: bool = True
    ):
        """Registra métricas de creación de profile"""
        
        # Obtener info del proxy
        result = await self.db.execute(
            select(Proxy).where(Proxy.id == proxy_id)
        )
        proxy = result.scalar_one_or_none()
        
        metric = ProfileMetrics(
            profile_id=profile_id,
            proxy_id=proxy_id,
            proxy_latency_ms=proxy_latency,
            proxy_country=proxy.country if proxy else None,
            proxy_city=proxy.city if proxy else None,
            proxy_session_id=proxy.session_id if proxy else None,
            creation_duration_seconds=creation_duration,
            creation_success=1 if success else 0,
            device_type=device_info.get("device_type"),
            device_brand=device_info.get("brand"),
            device_os=device_info.get("os"),
            adspower_response_time_ms=adspower_response_time,
            cookies_count=cookies_count
        )
        
        self.db.add(metric)
        
        # Actualizar stats del proxy
        await self._update_proxy_stats(proxy_id)
        
        await self.db.commit()
        
        logger.info(f"Metrics recorded for profile {profile_id}")
    
    async def _update_proxy_stats(self, proxy_id: int):
        """Actualiza estadísticas agregadas del proxy"""
        
        # Obtener o crear stats
        result = await self.db.execute(
            select(ProxyUsageStats).where(ProxyUsageStats.proxy_id == proxy_id)
        )
        stats = result.scalar_one_or_none()
        
        if not stats:
            stats = ProxyUsageStats(
                proxy_id=proxy_id,
                first_used_at=datetime.utcnow()
            )
            self.db.add(stats)
        
        # Calcular métricas agregadas
        result = await self.db.execute(
            select(
                func.count(ProfileMetrics.id).label('total'),
                func.avg(ProfileMetrics.proxy_latency_ms).label('avg_latency'),
                func.min(ProfileMetrics.proxy_latency_ms).label('min_latency'),
                func.max(ProfileMetrics.proxy_latency_ms).label('max_latency'),
                func.sum(ProfileMetrics.creation_success).label('successes')
            ).where(ProfileMetrics.proxy_id == proxy_id)
        )
        
        row = result.one()
        
        stats.total_profiles_created = row.total or 0
        stats.avg_latency_ms = row.avg_latency
        stats.min_latency_ms = row.min_latency
        stats.max_latency_ms = row.max_latency
        stats.success_rate = (row.successes / row.total * 100) if row.total > 0 else 100
        stats.last_used_at = datetime.utcnow()
        
        await self.db.commit()
    
    async def get_dashboard_stats(self) -> Dict:
        """Obtiene estadísticas para dashboard principal"""
        
        # Profiles
        profiles_result = await self.db.execute(
            select(
                func.count(Profile.id).label('total'),
                func.count(Profile.id).filter(Profile.status == ProfileStatus.READY).label('ready'),
                func.count(Profile.id).filter(Profile.created_at >= datetime.utcnow() - timedelta(days=7)).label('created_last_7_days')
            )
        )
        profiles = profiles_result.one()
        
        # Proxies
        proxies_result = await self.db.execute(
            select(
                func.count(Proxy.id).label('total'),
                func.count(Proxy.id).filter(Proxy.status == ProxyStatus.ACTIVE).label('active'),
                func.avg(Proxy.avg_response_time).label('avg_latency')
            )
        )
        proxies = proxies_result.one()
        
        # Métricas recientes
        metrics_result = await self.db.execute(
            select(
                func.avg(ProfileMetrics.creation_duration_seconds).label('avg_creation_time'),
                func.avg(ProfileMetrics.adspower_response_time_ms).label('avg_adspower_time'),
                func.sum(ProfileMetrics.cookies_count).label('total_cookies')
            ).where(
                ProfileMetrics.created_at >= datetime.utcnow() - timedelta(days=7)
            )
        )
        metrics = metrics_result.one()
        
        return {
            "profiles": {
                "total": profiles.total or 0,
                "ready": profiles.ready or 0,
                "created_last_7_days": profiles.created_last_7_days or 0
            },
            "proxies": {
                "total": proxies.total or 0,
                "active": proxies.active or 0,
                "avg_latency_ms": round(proxies.avg_latency or 0, 2)
            },
            "performance": {
                "avg_creation_time_seconds": round(metrics.avg_creation_time or 0, 2),
                "avg_adspower_response_ms": round(metrics.avg_adspower_time or 0, 2),
                "total_cookies_generated": metrics.total_cookies or 0
            }
        }
    
    async def get_proxy_performance_report(
        self,
        days: int = 30
    ) -> List[Dict]:
        """Reporte de rendimiento de proxies"""
        
        since = datetime.utcnow() - timedelta(days=days)
        
        result = await self.db.execute(
            select(
                Proxy.id,
                Proxy.city,
                Proxy.region,
                Proxy.country,
                ProxyUsageStats.total_profiles_created,
                ProxyUsageStats.avg_latency_ms,
                ProxyUsageStats.success_rate,
                ProxyUsageStats.total_rotations
            ).join(
                ProxyUsageStats,
                Proxy.id == ProxyUsageStats.proxy_id
            ).where(
                ProxyUsageStats.last_used_at >= since
            ).order_by(
                desc(ProxyUsageStats.total_profiles_created)
            )
        )
        
        proxies = []
        for row in result.all():
            proxies.append({
                "proxy_id": row.id,
                "location": f"{row.city}, {row.region}, {row.country}",
                "profiles_created": row.total_profiles_created,
                "avg_latency_ms": round(row.avg_latency_ms or 0, 2),
                "success_rate": round(row.success_rate or 0, 2),
                "rotations": row.total_rotations
            })
        
        return proxies
    
    async def get_creation_timeline(
        self,
        days: int = 30
    ) -> List[Dict]:
        """Timeline de creación de profiles"""
        
        since = datetime.utcnow() - timedelta(days=days)
        
        result = await self.db.execute(
            select(
                func.date(ProfileMetrics.created_at).label('date'),
                func.count(ProfileMetrics.id).label('count'),
                func.avg(ProfileMetrics.creation_duration_seconds).label('avg_duration'),
                func.avg(ProfileMetrics.proxy_latency_ms).label('avg_latency')
            ).where(
                ProfileMetrics.created_at >= since
            ).group_by(
                func.date(ProfileMetrics.created_at)
            ).order_by(
                func.date(ProfileMetrics.created_at)
            )
        )
        
        timeline = []
        for row in result.all():
            timeline.append({
                "date": row.date.isoformat(),
                "profiles_created": row.count,
                "avg_duration_seconds": round(row.avg_duration or 0, 2),
                "avg_latency_ms": round(row.avg_latency or 0, 2)
            })
        
        return timeline