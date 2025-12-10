# app/services/scheduler_service.py
"""
Servicio para programación de warming scripts con sincronización de timezone
"""
from typing import List, Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import datetime, timedelta
import pytz
from croniter import croniter
from loguru import logger

from app.models.scheduled_warming import (
    ScheduledWarming, 
    ScheduleFrequency, 
    ScheduledWarmingStatus
)
from app.schemas.scheduled_warming import ScheduledWarmingCreate

class SchedulerService:
    """Servicio de programación de warming"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_scheduled_warming(
        self,
        schedule_data: ScheduledWarmingCreate
    ) -> ScheduledWarming:
        """
        Crea warming programado
        
        Args:
            schedule_data: {
                "script_id": 1,
                "profile_ids": [1, 2, 3],
                "frequency": "daily",
                "scheduled_at": "2024-12-15T14:30:00",
                "timezone": "America/Guayaquil",
                "cron_expression": "0 14 * * *",  # Opcional
                "days_of_week": [1, 2, 3, 4, 5],  # Lunes a Viernes
                "max_executions": None,  # Infinito
                "expires_at": None
            }
        """
        
        # Convertir scheduled_at a UTC
        scheduled_at_utc = self._to_utc(
            schedule_data.scheduled_at,
            schedule_data.timezone
        )
        
        # Calcular próxima ejecución
        next_execution = self._calculate_next_execution(
            scheduled_at_utc,
            schedule_data.frequency,
            schedule_data.cron_expression,
            schedule_data.days_of_week
        )
        
        # Crear registro
        scheduled_warming = ScheduledWarming(
            script_id=schedule_data.script_id,
            profile_ids=schedule_data.profile_ids,
            frequency=schedule_data.frequency,
            scheduled_at=scheduled_at_utc,
            cron_expression=schedule_data.cron_expression,
            timezone=schedule_data.timezone,
            days_of_week=schedule_data.days_of_week,
            time_of_day=schedule_data.time_of_day,
            next_execution_at=next_execution,
            max_executions=schedule_data.max_executions,
            expires_at=schedule_data.expires_at,
            tags=schedule_data.tags or [],
            notes=schedule_data.notes
        )
        
        self.db.add(scheduled_warming)
        await self.db.commit()
        await self.db.refresh(scheduled_warming)
        
        logger.info(
            f"Scheduled warming created: script_id={schedule_data.script_id}, "
            f"next_execution={next_execution}"
        )
        
        return scheduled_warming
    
    async def get_pending_executions(self) -> List[ScheduledWarming]:
        """
        Obtiene warmings pendientes de ejecución
        
        Returns:
            Lista de ScheduledWarming cuya next_execution_at <= now
        """
        
        now = datetime.utcnow()
        
        result = await self.db.execute(
            select(ScheduledWarming).where(
                and_(
                    ScheduledWarming.is_active == True,
                    ScheduledWarming.status == ScheduledWarmingStatus.PENDING,
                    ScheduledWarming.next_execution_at <= now
                )
            )
        )
        
        return list(result.scalars().all())
    
    async def execute_scheduled_warming(
        self,
        scheduled_warming: ScheduledWarming
    ) -> Dict:
        """
        Ejecuta warming programado
        
        Llama al servicio de warming normal
        """
        
        from app.services.warming_script_service import WarmingScriptService
        from app.websocket.manager import connection_manager
        
        # Actualizar estado
        scheduled_warming.status = ScheduledWarmingStatus.RUNNING
        scheduled_warming.last_execution_at = datetime.utcnow()
        scheduled_warming.execution_count += 1
        await self.db.commit()
        
        try:
            # Ejecutar warming en profiles
            warming_service = WarmingScriptService(self.db)
            
            executions = []
            for profile_id in scheduled_warming.profile_ids:
                # Obtener computadora del profile
                from app.services.profile_service import ProfileService
                profile_service = ProfileService(self.db)
                
                profile = await profile_service.get_profile(profile_id)
                if not profile:
                    logger.warning(f"Profile {profile_id} not found")
                    continue
                
                # Crear ejecución
                execution = await warming_service.create_execution(
                    script_id=scheduled_warming.script_id,
                    profile_id=profile.id,
                    computer_id=profile.computer_id
                )
                
                executions.append(execution.id)
                
                # Enviar comando al agente
                script = await warming_service.get_script(scheduled_warming.script_id)
                
                await connection_manager.execute_warming(
                    computer_id=profile.computer_id,
                    execution_id=execution.id,
                    profile_id=profile.adspower_id,
                    script_actions=script.actions
                )
            
            # Actualizar estado
            scheduled_warming.success_count += 1
            scheduled_warming.status = ScheduledWarmingStatus.COMPLETED
            
            # Calcular próxima ejecución (si es recurrente)
            if scheduled_warming.frequency != ScheduleFrequency.ONCE:
                next_exec = self._calculate_next_execution(
                    datetime.utcnow(),
                    scheduled_warming.frequency,
                    scheduled_warming.cron_expression,
                    scheduled_warming.days_of_week
                )
                
                scheduled_warming.next_execution_at = next_exec
                scheduled_warming.status = ScheduledWarmingStatus.PENDING
            else:
                scheduled_warming.is_active = False
            
            # Verificar límites
            if scheduled_warming.max_executions:
                if scheduled_warming.execution_count >= scheduled_warming.max_executions:
                    scheduled_warming.is_active = False
            
            if scheduled_warming.expires_at:
                if datetime.utcnow() >= scheduled_warming.expires_at:
                    scheduled_warming.is_active = False
            
            await self.db.commit()
            
            return {
                "success": True,
                "executions": executions,
                "next_execution": scheduled_warming.next_execution_at
            }
        
        except Exception as e:
            logger.error(f"Scheduled warming execution failed: {e}")
            
            scheduled_warming.failure_count += 1
            scheduled_warming.status = ScheduledWarmingStatus.FAILED
            await self.db.commit()
            
            return {
                "success": False,
                "error": str(e)
            }
    
    def _to_utc(self, dt: datetime, timezone_str: str) -> datetime:
        """Convierte datetime a UTC"""
        
        if dt.tzinfo is None:
            # Asumir que está en el timezone especificado
            tz = pytz.timezone(timezone_str)
            dt = tz.localize(dt)
        
        return dt.astimezone(pytz.UTC)
    
    def _calculate_next_execution(
        self,
        base_dt: datetime,
        frequency: ScheduleFrequency,
        cron_expr: Optional[str] = None,
        days_of_week: Optional[List[int]] = None
    ) -> datetime:
        """Calcula próxima ejecución"""
        
        if frequency == ScheduleFrequency.ONCE:
            return base_dt
        
        elif frequency == ScheduleFrequency.DAILY:
            return base_dt + timedelta(days=1)
        
        elif frequency == ScheduleFrequency.WEEKLY:
            # Buscar próximo día de la semana válido
            if not days_of_week:
                return base_dt + timedelta(weeks=1)
            
            current_weekday = base_dt.weekday()
            
            for i in range(1, 8):
                next_day = (current_weekday + i) % 7
                if next_day in days_of_week:
                    return base_dt + timedelta(days=i)
            
            return base_dt + timedelta(weeks=1)
        
        elif frequency == ScheduleFrequency.MONTHLY:
            # Mismo día del próximo mes
            if base_dt.month == 12:
                return base_dt.replace(year=base_dt.year + 1, month=1)
            else:
                return base_dt.replace(month=base_dt.month + 1)
        
        elif frequency == ScheduleFrequency.CUSTOM_CRON and cron_expr:
            # Usar croniter para calcular
            cron = croniter(cron_expr, base_dt)
            return cron.get_next(datetime)
        
        return base_dt