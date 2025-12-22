# adspower-orchestrator2/app/services/warming_batch_executor.py
"""
Ejecutor de batches de warming con sincronización distribuida
Coordina múltiples agentes para ejecutar acciones en paralelo
"""
from typing import List, Dict, Optional, Set
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import datetime
from loguru import logger
import asyncio
import uuid

from app.models.warming_script import WarmingScript, WarmingExecution, ExecutionStatus
from app.models.profile import Profile, ProfileStatus
from app.models.computer import Computer, ComputerStatus
from app.services.warming_sync_service import warming_sync_service
from app.core.redis_messaging import redis_messaging


class BatchExecution:
    """Representa una ejecución batch"""
    
    def __init__(
        self,
        batch_id: str,
        script_id: int,
        profile_ids: List[int],
        total_actions: int
    ):
        self.batch_id = batch_id
        self.script_id = script_id
        self.profile_ids = profile_ids
        self.total_actions = total_actions
        
        # Ejecuciones individuales: {profile_id: execution_id}
        self.executions: Dict[int, int] = {}
        
        # Estado
        self.status = "running"
        self.started_at = datetime.utcnow()
        self.completed_at: Optional[datetime] = None
        
        # Métricas
        self.profiles_completed: Set[int] = set()
        self.profiles_failed: Set[int] = set()
    
    def add_execution(self, profile_id: int, execution_id: int):
        """Registra una ejecución individual"""
        self.executions[profile_id] = execution_id
    
    def mark_completed(self, profile_id: int):
        """Marca un profile como completado"""
        self.profiles_completed.add(profile_id)
        self._check_completion()
    
    def mark_failed(self, profile_id: int):
        """Marca un profile como fallido"""
        self.profiles_failed.add(profile_id)
        self._check_completion()
    
    def _check_completion(self):
        """Verifica si el batch está completo"""
        total_finished = len(self.profiles_completed) + len(self.profiles_failed)
        
        if total_finished >= len(self.profile_ids):
            self.status = "completed"
            self.completed_at = datetime.utcnow()
    
    def get_progress(self) -> int:
        """Retorna progreso del batch (0-100)"""
        total_finished = len(self.profiles_completed) + len(self.profiles_failed)
        return int((total_finished / len(self.profile_ids)) * 100)
    
    def get_summary(self) -> Dict:
        """Retorna resumen del batch"""
        return {
            "batch_id": self.batch_id,
            "script_id": self.script_id,
            "status": self.status,
            "total_profiles": len(self.profile_ids),
            "completed": len(self.profiles_completed),
            "failed": len(self.profiles_failed),
            "progress": self.get_progress(),
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": (
                (self.completed_at or datetime.utcnow()) - self.started_at
            ).total_seconds()
        }


class WarmingBatchExecutor:
    """Ejecutor de batches con sincronización distribuida"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        
        # Batches activos: {batch_id: BatchExecution}
        self.active_batches: Dict[str, BatchExecution] = {}
    
    async def execute_batch(
        self,
        script_id: int,
        profile_ids: List[int]
    ) -> Dict:
        """
        Ejecuta un batch de warming en paralelo sincronizado
        
        Returns:
            {
                "batch_id": "uuid",
                "total_profiles": 5,
                "executions": [123, 124, ...],
                "message": "Batch started"
            }
        """
        
        # Validar script
        script = await self._get_script(script_id)
        if not script:
            raise ValueError(f"Script {script_id} not found")
        
        # Validar profiles
        profiles = await self._get_profiles(profile_ids)
        if not profiles:
            raise ValueError("No valid profiles found")
        
        # Agrupar profiles por computadora
        profiles_by_computer = self._group_by_computer(profiles)
        
        # Verificar agentes conectados
        from app.websocket.manager import connection_manager
        connected_agents = connection_manager.get_connected_agents()
        
        # Filtrar solo computadoras online
        online_profiles = []
        offline_count = 0
        
        for computer_id, computer_profiles in profiles_by_computer.items():
            if computer_id in connected_agents:
                online_profiles.extend(computer_profiles)
            else:
                offline_count += len(computer_profiles)
                logger.warning(
                    f"Computer {computer_id} offline, skipping {len(computer_profiles)} profiles"
                )
        
        if not online_profiles:
            raise ValueError("No profiles with online computers")
        
        # Crear batch
        batch_id = str(uuid.uuid4())
        
        batch = BatchExecution(
            batch_id=batch_id,
            script_id=script_id,
            profile_ids=[p.id for p in online_profiles],
            total_actions=len(script.actions)
        )
        
        self.active_batches[batch_id] = batch
        
        logger.info(
            f"Starting batch {batch_id}: "
            f"{len(online_profiles)} profiles, {len(script.actions)} actions"
        )
        
        # Crear barreras de sincronización para cada acción
        for action_index in range(len(script.actions)):
            await warming_sync_service.create_barrier(
                batch_id=batch_id,
                action_index=action_index,
                total_agents=len(online_profiles),
                timeout_seconds=90  # 90 segundos por acción
            )
        
        # Crear ejecuciones y enviar comandos
        execution_ids = []
        
        for profile in online_profiles:
            try:
                # Crear ejecución en DB
                execution = await self._create_execution(
                    script_id=script_id,
                    profile_id=profile.id,
                    computer_id=profile.computer_id
                )
                
                execution_ids.append(execution.id)
                batch.add_execution(profile.id, execution.id)
                
                # Publicar comando via Redis con batch_id
                await redis_messaging.publish_warming_command(
                    computer_id=profile.computer_id,
                    execution_id=execution.id,
                    profile_id=profile.adspower_id,
                    script_actions=script.actions,
                    batch_id=batch_id  # ✅ NUEVO: Incluir batch_id
                )
                
                logger.info(
                    f"✓ Warming command published: "
                    f"Execution {execution.id}, Profile {profile.id}"
                )
            
            except Exception as e:
                logger.error(f"Error creating execution for profile {profile.id}: {e}")
                batch.mark_failed(profile.id)
        
        # Incrementar contador del script
        await self._increment_script_usage(script_id)
        
        # Retornar resultado
        return {
            "batch_id": batch_id,
            "total_profiles": len(profile_ids),
            "online_profiles": len(online_profiles),
            "offline_profiles": offline_count,
            "executions": execution_ids,
            "message": (
                f"Batch started: {len(online_profiles)} profiles executing in parallel"
                + (f", {offline_count} profiles skipped (offline)" if offline_count > 0 else "")
            )
        }
    
    async def _get_script(self, script_id: int) -> Optional[WarmingScript]:
        """Obtiene script"""
        result = await self.db.execute(
            select(WarmingScript).where(WarmingScript.id == script_id)
        )
        return result.scalar_one_or_none()
    
    async def _get_profiles(self, profile_ids: List[int]) -> List[Profile]:
        """Obtiene profiles válidos"""
        result = await self.db.execute(
            select(Profile).where(
                and_(
                    Profile.id.in_(profile_ids),
                    Profile.status.in_([ProfileStatus.READY, ProfileStatus.ACTIVE])
                )
            )
        )
        return list(result.scalars().all())
    
    def _group_by_computer(self, profiles: List[Profile]) -> Dict[int, List[Profile]]:
        """Agrupa profiles por computadora"""
        grouped = {}
        
        for profile in profiles:
            if profile.computer_id not in grouped:
                grouped[profile.computer_id] = []
            grouped[profile.computer_id].append(profile)
        
        return grouped
    
    async def _create_execution(
        self,
        script_id: int,
        profile_id: int,
        computer_id: int
    ) -> WarmingExecution:
        """Crea ejecución en DB"""
        
        execution = WarmingExecution(
            script_id=script_id,
            profile_id=profile_id,
            computer_id=computer_id,
            status=ExecutionStatus.QUEUED,
            progress=0,
            actions_completed=0,
            actions_failed=0,
            execution_log=[]
        )
        
        self.db.add(execution)
        await self.db.commit()
        await self.db.refresh(execution)
        
        return execution
    
    async def _increment_script_usage(self, script_id: int):
        """Incrementa contador de uso del script"""
        result = await self.db.execute(
            select(WarmingScript).where(WarmingScript.id == script_id)
        )
        script = result.scalar_one_or_none()
        
        if script:
            script.times_used += 1
            await self.db.commit()
    
    def mark_execution_completed(self, execution_id: int, profile_id: int):
        """Marca ejecución como completada"""
        
        # Buscar batch correspondiente
        for batch in self.active_batches.values():
            if profile_id in batch.executions:
                if batch.executions[profile_id] == execution_id:
                    batch.mark_completed(profile_id)
                    logger.debug(f"Batch {batch.batch_id}: Profile {profile_id} completed")
                    break
    
    def mark_execution_failed(self, execution_id: int, profile_id: int):
        """Marca ejecución como fallida"""
        
        for batch in self.active_batches.values():
            if profile_id in batch.executions:
                if batch.executions[profile_id] == execution_id:
                    batch.mark_failed(profile_id)
                    logger.debug(f"Batch {batch.batch_id}: Profile {profile_id} failed")
                    break
    
    async def cancel_batch(self, batch_id: str):
        """Cancela un batch completo"""
        
        if batch_id not in self.active_batches:
            logger.warning(f"Batch {batch_id} not found")
            return
        
        batch = self.active_batches[batch_id]
        
        # Cancelar barreras
        await warming_sync_service.cancel_batch(batch_id)
        
        # Actualizar estado
        batch.status = "cancelled"
        batch.completed_at = datetime.utcnow()
        
        logger.info(f"Batch {batch_id} cancelled")
    
    def get_batch_status(self, batch_id: str) -> Optional[Dict]:
        """Obtiene estado de un batch"""
        
        batch = self.active_batches.get(batch_id)
        
        if not batch:
            return None
        
        return batch.get_summary()
    
    async def cleanup_completed_batches(self):
        """Limpia batches completados"""
        
        to_remove = []
        
        for batch_id, batch in self.active_batches.items():
            if batch.status in ["completed", "cancelled"]:
                # Verificar que tenga más de 5 minutos
                age = (datetime.utcnow() - (batch.completed_at or batch.started_at)).total_seconds()
                
                if age > 300:  # 5 minutos
                    to_remove.append(batch_id)
                    
                    # Limpiar barreras
                    await warming_sync_service.remove_batch(batch_id)
        
        for batch_id in to_remove:
            del self.active_batches[batch_id]
        
        if to_remove:
            logger.info(f"Cleaned {len(to_remove)} completed batches")